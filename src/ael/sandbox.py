from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_IMAGE = "kizz/ael-runner:0.1.0-alpha.1"
DEFAULT_CODEX_IMAGE = "kizz/ael-codex-runner:0.146.0"
DEFAULT_EGRESS_IMAGE = "kizz/ael-egress-proxy:0.1.0-alpha.1"
DEFAULT_TIMEOUT_SECONDS = 900
MAX_AUTH_FILE_BYTES = 2 * 1024 * 1024
OPENAI_ALLOWED_HOSTS = ("api.openai.com", "auth.openai.com", "chatgpt.com")
NETWORK_POLICIES = ("none", "openai-proxy")
_RESOURCE_VALUE = re.compile(r"^[1-9][0-9]*(?:[bkmg])?$", re.IGNORECASE)
_CPU_VALUE = re.compile(r"^(?:[1-9][0-9]*|0\.[0-9]+|[1-9][0-9]*\.[0-9]+)$")
_IMAGE_REFERENCE = re.compile(
    r"^(?:[a-zA-Z0-9.-]+(?::[0-9]+)?/)?"
    r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*"
    r"(?::[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}|@sha256:[a-f0-9]{64})?$"
)


class SandboxError(RuntimeError):
    """Raised when a sandbox request violates policy or cannot execute."""


@dataclass(frozen=True)
class SandboxResult:
    container_name: str
    image: str
    image_id: str
    fixture_sha256: str
    exit_code: int
    duration_ms: int
    output: Path


def _run(
    command: Sequence[str],
    *,
    capture_output: bool = False,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
    )


def docker_doctor() -> dict[str, str]:
    if shutil.which("docker") is None:
        raise SandboxError("docker executable is not available")
    result = _run(
        ["docker", "version", "--format", "{{.Client.Version}}|{{.Server.Version}}"],
        capture_output=True,
        timeout=20,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SandboxError(f"docker engine is unavailable: {detail}")
    client, separator, server = result.stdout.strip().partition("|")
    if not separator or not client or not server:
        raise SandboxError("docker version output did not expose client and server versions")
    return {"client_version": client, "server_version": server}


def build_image(context: Path, tag: str = DEFAULT_IMAGE) -> str:
    docker_doctor()
    _validate_image_reference(tag)
    context = context.resolve()
    dockerfile = context / "Dockerfile"
    if not dockerfile.is_file():
        raise SandboxError(f"missing Dockerfile: {dockerfile}")
    result = _run(["docker", "build", "--pull=false", "--tag", tag, str(context)])
    if result.returncode != 0:
        raise SandboxError(f"docker build failed with exit code {result.returncode}")
    return inspect_image(tag)


def inspect_image(image: str) -> str:
    _validate_image_reference(image)
    result = _run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        capture_output=True,
        timeout=20,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SandboxError(f"runner image is unavailable: {image}: {detail}")
    image_id = result.stdout.strip()
    if not image_id.startswith("sha256:"):
        raise SandboxError(f"runner image did not expose a content digest: {image_id}")
    return image_id


def tree_sha256(root: Path) -> str:
    root = root.resolve()
    if not root.is_dir():
        raise SandboxError(f"fixture must be a directory: {root}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise SandboxError(f"tree must not contain symlinks: {relative}")
        elif path.is_dir():
            digest.update(f"D\0{relative}\n".encode())
        elif path.is_file():
            digest.update(f"F\0{relative}\0".encode())
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            digest.update(b"\n")
        else:
            raise SandboxError(f"tree contains a non-regular entry: {relative}")
    return digest.hexdigest()


def _validate_resource_value(label: str, value: str) -> None:
    if not _RESOURCE_VALUE.fullmatch(value):
        raise SandboxError(f"{label} must be a positive Docker size such as 256m or 2g")


def _validate_image_reference(image: str) -> None:
    if not _IMAGE_REFERENCE.fullmatch(image):
        raise SandboxError(f"invalid Docker image reference: {image!r}")


def _validate_cpu_value(value: str) -> None:
    if not _CPU_VALUE.fullmatch(value) or float(value) <= 0:
        raise SandboxError("cpus must be a positive number such as 0.5 or 2")


def _contains_symlink(path: Path) -> bool:
    candidate = path.absolute()
    while True:
        if candidate.is_symlink():
            return True
        parent = candidate.parent
        if parent == candidate:
            return False
        candidate = parent


def _prepare_paths(fixture: Path, output: Path) -> tuple[Path, Path]:
    if _contains_symlink(fixture):
        raise SandboxError("fixture path and its existing parents must not be symlinks")
    if _contains_symlink(output):
        raise SandboxError("output path and its existing parents must not be symlinks")
    fixture = fixture.resolve()
    output = output.resolve()
    if not fixture.is_dir():
        raise SandboxError(f"fixture must be a directory: {fixture}")
    if output == fixture or output.is_relative_to(fixture) or fixture.is_relative_to(output):
        raise SandboxError("fixture and output directories must not contain one another")
    if output.exists():
        if not output.is_dir():
            raise SandboxError(f"output must be a directory: {output}")
        if any(output.iterdir()):
            raise SandboxError(f"output directory must be empty: {output}")
    else:
        output.mkdir(parents=True, mode=0o700)
    return fixture, output


def _mount(source: Path, target: str, *, readonly: bool) -> str:
    if "," in str(source):
        raise SandboxError("Docker bind-mount source paths must not contain commas")
    options = ["type=bind", f"src={source}", f"dst={target}"]
    if readonly:
        options.append("readonly")
    return ",".join(options)


def _docker_checked(command: Sequence[str], description: str) -> str:
    result = _run(command, capture_output=True, timeout=30)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise SandboxError(f"{description} failed: {detail}")
    return result.stdout.strip()


def _start_egress_proxy(network_name: str, proxy_name: str, proxy_image: str) -> tuple[str, str]:
    proxy_image_id = inspect_image(proxy_image)
    _docker_checked(
        ["docker", "network", "create", "--driver", "bridge", "--internal", network_name],
        "internal network creation",
    )
    try:
        _docker_checked(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                proxy_name,
                "--network",
                network_name,
                "--network-alias",
                "ael-egress",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges=true",
                "--pids-limit",
                "64",
                "--memory",
                "128m",
                "--memory-swap",
                "128m",
                "--cpus",
                "0.5",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,noexec,size=16m,uid=65532,gid=65532,mode=1770",
                "--env",
                f"AEL_ALLOWED_HOSTS={','.join(OPENAI_ALLOWED_HOSTS)}",
                proxy_image,
            ],
            "egress proxy startup",
        )
        _docker_checked(
            ["docker", "network", "connect", "bridge", proxy_name],
            "egress proxy uplink",
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            state = _docker_checked(
                ["docker", "inspect", "--format", "{{.State.Running}}", proxy_name],
                "egress proxy readiness check",
            )
            if state == "true":
                networks = json.loads(
                    _docker_checked(
                        [
                            "docker",
                            "inspect",
                            "--format",
                            "{{json .NetworkSettings.Networks}}",
                            proxy_name,
                        ],
                        "egress proxy network inspection",
                    )
                )
                proxy_ip = networks.get(network_name, {}).get("IPAddress", "")
                try:
                    parsed_ip = ipaddress.ip_address(proxy_ip)
                except ValueError as exc:
                    raise SandboxError(
                        "egress proxy did not expose an internal IP address"
                    ) from exc
                if parsed_ip.version != 4 or not parsed_ip.is_private:
                    raise SandboxError(
                        "egress proxy internal address is not a private IPv4 address"
                    )
                return proxy_image_id, proxy_ip
            time.sleep(0.1)
        raise SandboxError("egress proxy did not become ready")
    except BaseException:
        _run(["docker", "rm", "--force", proxy_name], capture_output=True, timeout=20)
        _run(["docker", "network", "rm", network_name], capture_output=True, timeout=20)
        raise


def _stop_egress_proxy(network_name: str, proxy_name: str) -> str:
    log_text = ""
    try:
        logs = _run(["docker", "logs", proxy_name], capture_output=True, timeout=20)
        log_text = logs.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        pass
    finally:
        _run(["docker", "rm", "--force", proxy_name], capture_output=True, timeout=20)
        _run(["docker", "network", "rm", network_name], capture_output=True, timeout=20)
    return log_text


def _export_staged_output(staging: Path, output: Path) -> None:
    reserved = {"sandbox-invocation.json", "egress-proxy.log"}
    for path in sorted(staging.rglob("*")):
        relative = path.relative_to(staging).as_posix()
        if path.is_symlink():
            raise SandboxError(f"container output contains a symlink: {relative}")
        if not path.is_dir() and not path.is_file():
            raise SandboxError(f"container output contains a non-regular entry: {relative}")
    for name in reserved:
        if (staging / name).exists() or (staging / name).is_symlink():
            raise SandboxError(f"container output used reserved host metadata path: {name}")
    shutil.copytree(staging, output, dirs_exist_ok=True)


def _secret_values(auth_file: Path) -> list[bytes]:
    if auth_file.stat().st_size > MAX_AUTH_FILE_BYTES:
        raise SandboxError(f"credential file exceeds {MAX_AUTH_FILE_BYTES} bytes")
    try:
        document = json.loads(auth_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SandboxError("credential file is not readable JSON") from exc
    values: list[bytes] = []

    def collect(value: object) -> None:
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str) and len(value) >= 20:
            values.append(value.encode("utf-8"))

    collect(document)
    if not values:
        raise SandboxError("credential file contains no scannable secret values")
    return values


def _scan_exact_secret_values(output: Path, auth_file: Path) -> dict[str, object]:
    secrets = _secret_values(auth_file)
    hits: list[str] = []
    overlap = max(len(secret) for secret in secrets) - 1
    for path in sorted(output.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        matched = False
        tail = b""
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                payload = tail + chunk
                if any(secret in payload for secret in secrets):
                    matched = True
                    break
                tail = payload[-overlap:] if overlap else b""
        if matched:
            hits.append(path.relative_to(output).as_posix())
    return {
        "performed": True,
        "candidate_value_count": len(secrets),
        "exact_value_match_count": len(hits),
        "files_with_matches": hits,
        "scope": "persisted output only; does not inspect encrypted provider traffic",
    }


def run_container(
    fixture: Path,
    output: Path,
    command: Sequence[str],
    *,
    image: str = DEFAULT_IMAGE,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    cpus: str = "2",
    memory: str = "2g",
    pids_limit: int = 256,
    workspace_size: str = "1g",
    tmp_size: str = "256m",
    network_policy: str = "none",
    proxy_image: str = DEFAULT_EGRESS_IMAGE,
    auth_file: Path | None = None,
    intervention: Path | None = None,
    skill_name: str | None = None,
) -> SandboxResult:
    docker_doctor()
    if not command:
        raise SandboxError("container command is required")
    if timeout_seconds < 1:
        raise SandboxError("timeout_seconds must be positive")
    if pids_limit < 16:
        raise SandboxError("pids_limit must be at least 16")
    _validate_resource_value("memory", memory)
    _validate_resource_value("workspace_size", workspace_size)
    _validate_resource_value("tmp_size", tmp_size)
    _validate_cpu_value(cpus)
    _validate_image_reference(image)
    _validate_image_reference(proxy_image)
    if network_policy not in NETWORK_POLICIES:
        raise SandboxError(f"unsupported network policy: {network_policy}")
    if network_policy == "none" and auth_file is not None:
        raise SandboxError("credential injection requires the openai-proxy network policy")
    resolved_auth: Path | None = None
    if auth_file is not None:
        if _contains_symlink(auth_file):
            raise SandboxError("credential path and its existing parents must not be symlinks")
        resolved_auth = auth_file.resolve()
        if not resolved_auth.is_file():
            raise SandboxError(f"credential file is unavailable: {resolved_auth}")
    resolved_intervention: Path | None = None
    intervention_sha256: str | None = None
    if intervention is not None:
        if _contains_symlink(intervention):
            raise SandboxError("intervention path and its existing parents must not be symlinks")
        resolved_intervention = intervention.resolve()
        if not resolved_intervention.is_dir():
            raise SandboxError(f"intervention must be a directory: {resolved_intervention}")
        if not skill_name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill_name):
            raise SandboxError("skill_name must be a lowercase kebab-case identifier")
        intervention_sha256 = tree_sha256(resolved_intervention)
    fixture, output = _prepare_paths(fixture, output)
    fixture_before = tree_sha256(fixture)
    image_id = inspect_image(image)
    user_id = os.getuid()
    group_id = os.getgid()
    container_name = f"ael-run-{uuid.uuid4().hex[:12]}"
    network_name = f"ael-net-{uuid.uuid4().hex[:12]}"
    proxy_name = f"ael-proxy-{uuid.uuid4().hex[:12]}"
    proxy_image_id: str | None = None
    proxy_ip: str | None = None
    docker_network = "none"
    if network_policy == "openai-proxy":
        docker_network = network_name
    staging = Path(tempfile.mkdtemp(prefix="ael-output-"))
    try:
        docker_command = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--init",
            "--network",
            docker_network,
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges=true",
            "--pids-limit",
            str(pids_limit),
            "--memory",
            memory,
            "--memory-swap",
            memory,
            "--cpus",
            cpus,
            "--user",
            f"{user_id}:{group_id}",
            "--workdir",
            "/workspace",
            "--env",
            "HOME=/workspace/home",
            "--env",
            "CODEX_HOME=/workspace/home/.codex",
            "--env",
            "TMPDIR=/tmp",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--tmpfs",
            f"/workspace:rw,nosuid,nodev,size={workspace_size},uid={user_id},gid={group_id},mode=0750",
            "--tmpfs",
            f"/tmp:rw,nosuid,nodev,noexec,size={tmp_size},uid={user_id},gid={group_id},mode=1770",
            "--mount",
            _mount(fixture, "/fixture", readonly=True),
            "--mount",
            _mount(staging, "/output", readonly=False),
        ]
        if resolved_auth is not None:
            docker_command.extend(
                [
                    "--mount",
                    _mount(resolved_auth, "/run/ael-secrets/codex-auth.json", readonly=True),
                ]
            )
        if resolved_intervention is not None:
            docker_command.extend(
                ["--mount", _mount(resolved_intervention, "/intervention", readonly=True)]
            )
            docker_command.extend(["--env", f"AEL_SKILL_NAME={skill_name}"])
        proxy_started = False
        if network_policy == "openai-proxy":
            proxy_image_id, proxy_ip = _start_egress_proxy(network_name, proxy_name, proxy_image)
            proxy_started = True
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                docker_command.extend(["--env", f"{key}=http://{proxy_ip}:3128"])
            docker_command.extend(["--env", "NO_PROXY=localhost,127.0.0.1"])
            docker_command.extend(["--env", "no_proxy=localhost,127.0.0.1"])
            docker_command.extend(["--dns", "127.0.0.1"])
        docker_command.extend([image, *command])
        started = time.monotonic()
        proxy_log = ""
        try:
            try:
                completed = _run(docker_command, timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                _run(["docker", "rm", "--force", container_name], capture_output=True, timeout=20)
                raise SandboxError(
                    f"container exceeded {timeout_seconds}s and was removed"
                ) from exc
            except KeyboardInterrupt:
                _run(["docker", "rm", "--force", container_name], capture_output=True, timeout=20)
                raise
        finally:
            if proxy_started:
                proxy_log = _stop_egress_proxy(network_name, proxy_name)
        duration_ms = round((time.monotonic() - started) * 1000)
        fixture_after = tree_sha256(fixture)
        if fixture_after != fixture_before:
            raise SandboxError("read-only fixture identity changed during the run")
        secret_scan: dict[str, object] = {
            "performed": False,
            "candidate_value_count": 0,
            "exact_value_match_count": 0,
            "files_with_matches": [],
            "scope": "not applicable",
        }
        if resolved_auth is not None:
            secret_scan = _scan_exact_secret_values(staging, resolved_auth)
        if secret_scan["exact_value_match_count"]:
            raise SandboxError("credential material was detected in persisted run output")
        _export_staged_output(staging, output)
        if proxy_log:
            (output / "egress-proxy.log").write_text(proxy_log, encoding="utf-8")
        invocation = {
            "schema_version": "ael.sandbox-invocation/0.1",
            "container_name": container_name,
            "image": image,
            "image_id": image_id,
            "network": network_policy,
            "allowed_egress_hosts": list(OPENAI_ALLOWED_HOSTS)
            if network_policy == "openai-proxy"
            else [],
            "proxy_image": proxy_image if network_policy == "openai-proxy" else None,
            "proxy_image_id": proxy_image_id,
            "agent_dns": "disabled" if network_policy == "openai-proxy" else "none_network",
            "credential_injected": resolved_auth is not None,
            "intervention_injected": resolved_intervention is not None,
            "intervention_name": skill_name if resolved_intervention is not None else None,
            "intervention_sha256": intervention_sha256,
            "secret_persistence_scan": secret_scan,
            "output_export": "validated_staging_copy",
            "root_filesystem": "read_only",
            "capabilities": "all_dropped",
            "no_new_privileges": True,
            "fixture_sha256_before": fixture_before,
            "fixture_sha256_after": fixture_after,
            "command": list(command),
            "limits": {
                "timeout_seconds": timeout_seconds,
                "cpus": cpus,
                "memory": memory,
                "pids": pids_limit,
                "workspace_tmpfs": workspace_size,
                "tmp_tmpfs": tmp_size,
            },
            "exit_code": completed.returncode,
            "duration_ms": duration_ms,
        }
        (output / "sandbox-invocation.json").write_text(
            json.dumps(invocation, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return SandboxResult(
            container_name=container_name,
            image=image,
            image_id=image_id,
            fixture_sha256=fixture_before,
            exit_code=completed.returncode,
            duration_ms=duration_ms,
            output=output,
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)
