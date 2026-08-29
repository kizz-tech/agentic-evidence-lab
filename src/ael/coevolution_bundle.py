"""Strict filesystem adapter for the family-local AEL-CEP policy kernel.

The :mod:`ael.coevolution` module is intentionally a pure policy kernel.  This
module is the narrow seam that turns its JSON-like values into immutable files:
it owns byte parsing, schema loading, path/size limits, atomic writes, and
descriptive Markdown rendering.  It does not grant promotion authority or
execute evaluator code.
"""

from __future__ import annotations

import hashlib
import json
import math
import ntpath
import os
import posixpath
import stat
import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from importlib import resources
from pathlib import Path
from typing import Any, NoReturn

import jsonschema

import ael.coevolution as core

MAX_FILE_BYTES = 2 * 1024 * 1024
"""Maximum bytes read from any user-supplied JSON input."""

# Keep malformed-input validation below the 2 MiB byte ceiling as well as the
# core's graph limits.  Stage 0 bundles are far smaller; these are adapter
# ceilings, not a promise that every bound-sized ledger is operationally useful.
MAX_RECORDS = 2_048
MAX_EDGES = 10_000
MAX_ARRAY_ITEMS = 20_000
MAX_DEPTH = 64
MAX_REQUEST_BYTES = MAX_FILE_BYTES

_DRAFT_SCHEMA = "https://json-schema.org/draft/2020-12/schema"
_SCHEMA_FILES = {"protocol": "protocol.schema.json", "bundle": "bundle.schema.json"}
_REQUEST_FIELDS = {
    "evaluator_release",
    "score_payload",
    "actor",
    "retained_surfaces",
    "required_surfaces",
    "changes",
    "deterministic_code",
}
_REQUEST_REQUIRED = {"evaluator_release", "score_payload"}
_MAX_SCHEMA_ERROR_MESSAGE = 512


class CoevolutionBundleError(ValueError):
    """A deterministic, reason-coded adapter error.

    ``reason`` is deliberately a short machine-readable code.  Details are
    stable path-oriented text and never include source bytes or credentials.
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(reason if not detail else f"{reason}: {detail}")


# A shorter name is useful to callers that do not need to distinguish the
# policy kernel from its filesystem adapter.
AdapterError = CoevolutionBundleError


def _fail(reason: str, detail: str) -> NoReturn:
    raise CoevolutionBundleError(reason, detail)


def _as_path(value: os.PathLike[str] | str, label: str) -> Path:
    try:
        result = Path(value)
    except (TypeError, ValueError):
        _fail("invalid_path", f"{label} is not a filesystem path")
    if "\x00" in str(result):
        _fail("unsafe_path", f"{label} contains NUL")
    return result


def _path_components(path: Path) -> list[Path]:
    absolute = path.absolute()
    components: list[Path] = []
    current = absolute
    while True:
        components.append(current)
        parent = current.parent
        if parent == current:
            break
        current = parent
    return list(reversed(components))


def _contains_symlink(path: Path) -> bool:
    # macOS exposes /var and /tmp as conventional links to /private/*; these
    # are system mount aliases, not caller-controlled output parents. All
    # other links, including links introduced inside a temporary root, fail
    # closed.
    system_aliases = {Path("/var"), Path("/tmp")}
    return any(
        candidate.is_symlink() and candidate not in system_aliases
        for candidate in _path_components(path)
    )


def _assert_regular_file(path: Path, label: str, *, max_bytes: int = MAX_FILE_BYTES) -> int:
    if _contains_symlink(path):
        _fail("unsafe_symlink", f"{label} must not use symlinks")
    try:
        info = path.stat()
    except FileNotFoundError:
        _fail("missing_file", f"{label} does not exist")
    except OSError as exc:
        _fail("file_unreadable", f"{label} metadata is unavailable: {exc.__class__.__name__}")
    if not stat.S_ISREG(info.st_mode):
        _fail("non_regular_file", f"{label} must be a regular file")
    if info.st_size > max_bytes:
        _fail("size_limit", f"{label} exceeds {max_bytes} bytes")
    return int(info.st_size)


def _assert_output_parent(path: Path, *, create: bool = True) -> Path:
    parent = path.parent
    if _contains_symlink(parent):
        _fail("unsafe_symlink", "output parent must not use symlinks")
    # A missing parent is safe to create only when every existing ancestor is
    # a regular directory and not a symlink.
    missing: list[Path] = []
    current = parent
    while not current.exists():
        missing.append(current)
        next_parent = current.parent
        if next_parent == current:
            _fail("output_parent", "output parent cannot be resolved")
        current = next_parent
    if current.is_symlink() and current not in {Path("/var"), Path("/tmp")}:
        _fail("unsafe_symlink", "output parent must not use symlinks")
    if not current.is_dir():
        _fail("output_parent", "output parent must be a directory")
    if missing and not create:
        _fail("output_parent", "output parent is missing in check mode")
    for directory in reversed(missing):
        try:
            directory.mkdir()
        except FileExistsError:
            if directory.is_symlink() or not directory.is_dir():
                _fail("unsafe_symlink", "output parent changed to an unsafe entry")
        except OSError as exc:
            _fail("output_parent", f"cannot create output parent: {exc.__class__.__name__}")
    if _contains_symlink(parent) or not parent.is_dir():
        _fail("unsafe_symlink", "output parent must remain a regular directory")
    return parent


def _assert_output_path(path: Path, label: str = "output", *, create_parent: bool = True) -> Path:
    _assert_output_parent(path, create=create_parent)
    if path.is_symlink():
        _fail("unsafe_symlink", f"{label} must not be a symlink")
    if path.exists() and not path.is_file():
        _fail("non_regular_file", f"{label} must be a regular file")
    return path


def _assert_distinct_output(output: Path, inputs: Sequence[Path], label: str) -> None:
    """Reject replacing any source file, including hard-link aliases."""

    output_absolute = output.absolute()
    for source in inputs:
        source_absolute = source.absolute()
        if output_absolute == source_absolute:
            _fail("input_mutation", f"{label} must not replace an input")
        try:
            if output.exists() and source.exists() and os.path.samefile(output, source):
                _fail("input_mutation", f"{label} must not replace an input")
        except OSError:
            # Missing output or inaccessible metadata is handled by the normal
            # output path checks; do not turn it into an ambient probe.
            continue


class _Pairs(dict[str, Any]):
    """JSON object constructor that rejects duplicate members."""

    def __init__(self, pairs: list[tuple[str, Any]]) -> None:
        seen: set[str] = set()
        for key, value in pairs:
            if key in seen:
                _fail("duplicate_json_member", f"duplicate JSON member {key!r}")
            seen.add(key)
            self[key] = value


def _reject_constant(value: str) -> NoReturn:
    _fail("nonfinite", f"JSON constant {value} is not finite")


def _parse_json(raw: bytes, label: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        _fail("invalid_utf8", f"{label} is not valid UTF-8")
    try:
        return json.loads(
            text,
            object_pairs_hook=_Pairs,
            parse_constant=_reject_constant,
        )
    except CoevolutionBundleError:
        raise
    except json.JSONDecodeError as exc:
        _fail("invalid_json", f"{label} at line {exc.lineno}, column {exc.colno}")
    except RecursionError:
        _fail("depth_limit", f"{label} exceeds maximum JSON depth {MAX_DEPTH}")
    except (TypeError, ValueError) as exc:
        _fail("invalid_json", f"{label}: {exc.__class__.__name__}")


def _read_json(
    path: os.PathLike[str] | str, label: str, *, max_bytes: int = MAX_FILE_BYTES
) -> tuple[Any, bytes]:
    candidate = _as_path(path, label)
    _assert_regular_file(candidate, label, max_bytes=max_bytes)
    try:
        with candidate.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
    except OSError as exc:
        _fail("file_unreadable", f"{label} cannot be read: {exc.__class__.__name__}")
    if len(raw) > max_bytes:
        _fail("size_limit", f"{label} exceeds {max_bytes} bytes")
    return _parse_json(raw, label), raw


def _scan_string(value: str, path: str) -> None:
    if "\x00" in value:
        _fail("unsafe_reference", f"{path} contains NUL")
    if "file://" in value.casefold():
        _fail("unsafe_reference", f"{path} contains a file:// reference")
    if posixpath.isabs(value) or ntpath.isabs(value):
        _fail("unsafe_reference", f"{path} contains an absolute path")
    path_parts = value.replace("\\", "/").split("/")
    if ".." in path_parts:
        _fail("unsafe_reference", f"{path} contains directory traversal")


def _scan_value(
    value: Any, path: str = "value", *, depth: int = 0, arrays: list[int] | None = None
) -> None:
    """Apply adapter-wide JSON limits and reject unsafe path-like strings."""

    if depth > MAX_DEPTH:
        _fail("depth_limit", f"{path} exceeds maximum JSON depth {MAX_DEPTH}")
    if isinstance(value, str):
        _scan_string(value, path)
        return
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            _fail("nonfinite", f"{path} must contain only finite numbers")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                _fail("invalid_json_value", f"{path} has a non-string object key")
            _scan_string(key, f"{path}.<key>")
            _scan_value(child, f"{path}.{key}", depth=depth + 1, arrays=arrays)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if len(value) > MAX_ARRAY_ITEMS:
            _fail("array_limit", f"{path} exceeds {MAX_ARRAY_ITEMS} items")
        for index, child in enumerate(value):
            _scan_value(child, f"{path}[{index}]", depth=depth + 1, arrays=arrays)
        return
    _fail("invalid_json_value", f"{path} contains unsupported type {type(value).__name__}")


def _schema_resource(kind: str) -> Any:
    filename = _SCHEMA_FILES.get(kind)
    if filename is None:
        _fail("schema_kind", f"unknown schema kind {kind}")
    try:
        package = resources.files("ael.coevolution_schemas")
    except (ModuleNotFoundError, ImportError):
        try:
            package = resources.files("ael").joinpath("coevolution_schemas")
        except (ModuleNotFoundError, ImportError) as exc:
            _fail(
                "schema_unavailable",
                f"AEL-CEP schema package is unavailable: {exc.__class__.__name__}",
            )
    resource = package.joinpath(filename)
    try:
        if not resource.is_file():
            _fail("schema_unavailable", f"AEL-CEP {kind} schema resource is missing")
        raw = resource.read_bytes()
    except CoevolutionBundleError:
        raise
    except (OSError, UnicodeError) as exc:
        _fail(
            "schema_unavailable", f"AEL-CEP {kind} schema cannot be read: {exc.__class__.__name__}"
        )
    return _parse_schema(raw, kind)


def _parse_schema(raw: bytes, kind: str) -> Mapping[str, Any]:
    if len(raw) > MAX_FILE_BYTES:
        _fail("schema_size_limit", f"AEL-CEP {kind} schema exceeds {MAX_FILE_BYTES} bytes")
    data = _parse_json(raw, f"{kind} schema")
    _scan_value(data, f"{kind} schema")
    if not isinstance(data, Mapping):
        _fail("schema_invalid", f"AEL-CEP {kind} schema must be an object")
    if data.get("$schema") != _DRAFT_SCHEMA:
        _fail("schema_dialect", f"AEL-CEP {kind} schema must declare Draft 2020-12")
    try:
        jsonschema.Draft202012Validator.check_schema(data)
    except jsonschema.exceptions.SchemaError as exc:
        _fail("schema_invalid", f"AEL-CEP {kind} schema is invalid: {exc.message}")
    return data


def _schema_error_path(error: jsonschema.ValidationError) -> str:
    path = list(error.absolute_path)
    if not path:
        return "$"
    result = "$"
    for item in path:
        result += f"[{item}]" if isinstance(item, int) else f".{item}"
    return result


def _schema_error_has_unknown_field(error: jsonschema.ValidationError) -> bool:
    if error.validator in {"additionalProperties", "unevaluatedProperties"}:
        return True
    return any(_schema_error_has_unknown_field(child) for child in error.context)


def _bounded_schema_error_message(error: jsonschema.ValidationError) -> str:
    message = str(error.message)
    if len(message) <= _MAX_SCHEMA_ERROR_MESSAGE:
        return message
    return message[: _MAX_SCHEMA_ERROR_MESSAGE - 3] + "..."


def _select_schema_error(
    errors: Iterable[jsonschema.ValidationError],
) -> jsonschema.ValidationError | None:
    """Select one deterministic error without retaining the full error stream."""

    selected: jsonschema.ValidationError | None = None
    selected_key: tuple[str, str, str] | None = None
    for error in errors:
        key = (_schema_error_path(error), error.validator, _bounded_schema_error_message(error))
        if selected_key is None or key < selected_key:
            selected = error
            selected_key = key
    return selected


def _validate_schema(value: Any, kind: str) -> None:
    schema = _schema_resource(kind)
    validator = jsonschema.Draft202012Validator(schema)
    first = _select_schema_error(validator.iter_errors(value))
    if first is not None:
        reason = "unknown_field" if _schema_error_has_unknown_field(first) else "schema_violation"
        _fail(reason, f"{kind} {_schema_error_path(first)}: {_bounded_schema_error_message(first)}")


def _core_call(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except core.CoevolutionError as exc:
        raise CoevolutionBundleError(exc.reason, str(exc).split(": ", 1)[-1]) from exc
    except (TypeError, ValueError) as exc:
        _fail("core_validation", f"{function.__name__}: {exc.__class__.__name__}")


def _validate_protocol_value(protocol: Any) -> dict[str, Any]:
    _scan_value(protocol, "protocol")
    _validate_schema(protocol, "protocol")
    return _core_call(core.freeze_protocol, protocol)


def _validate_bundle_value(
    bundle: Any,
    *,
    protocol: Mapping[str, Any],
    predecessor: Mapping[str, Any] | None = None,
    predecessor_chain: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if predecessor is not None and predecessor_chain is not None:
        _fail(
            "predecessor_arguments",
            "supply predecessor or predecessor_chain, not both",
        )
    _scan_value(bundle, "bundle")
    if not isinstance(bundle, Mapping):
        _fail("invalid_type", "bundle must be a JSON object")
    if bundle.get("predecessor") is not None and predecessor is None and predecessor_chain is None:
        _fail(
            "predecessor_required",
            "bundle declares a predecessor but no predecessor path was supplied",
        )
    records = bundle.get("records")
    if isinstance(records, Sequence) and not isinstance(records, (str, bytes, bytearray)):
        if len(records) > MAX_RECORDS:
            _fail("record_limit", f"bundle.records exceeds {MAX_RECORDS} records")
        edge_count = 0
        for record in records:
            if isinstance(record, Mapping):
                dependencies = record.get("dependency_refs", ())
                if isinstance(dependencies, Mapping) or (
                    isinstance(dependencies, Sequence)
                    and not isinstance(dependencies, (str, bytes, bytearray))
                ):
                    edge_count += len(dependencies)
        if edge_count > MAX_EDGES:
            _fail("edge_limit", f"bundle dependency graph exceeds {MAX_EDGES} edges")
    _validate_schema(bundle, "bundle")
    return _core_call(
        core.validate_bundle,
        bundle,
        protocol=protocol,
        predecessor=predecessor,
        predecessor_chain=predecessor_chain,
    )


def _normalize_predecessor_paths(
    predecessor_path: os.PathLike[str] | str | None,
    predecessor_paths: Sequence[os.PathLike[str] | str] | None,
) -> tuple[Path, ...]:
    """Normalize the singular compatibility alias and an ordered chain."""

    if predecessor_path is not None and predecessor_paths is not None:
        _fail(
            "predecessor_arguments",
            "supply either predecessor_path or predecessor_paths, not both",
        )
    if predecessor_paths is None:
        if predecessor_path is None:
            return ()
        return (_as_path(predecessor_path, "predecessor bundle"),)
    if isinstance(predecessor_paths, (str, bytes, bytearray)) or not isinstance(
        predecessor_paths, Sequence
    ):
        _fail("invalid_type", "predecessor_paths must be an array of filesystem paths")
    if len(predecessor_paths) > MAX_DEPTH:
        _fail("depth_limit", f"predecessor_paths exceeds maximum depth {MAX_DEPTH}")
    return tuple(
        _as_path(item, f"predecessor bundle[{index}]")
        for index, item in enumerate(predecessor_paths)
    )


def _load_predecessor_chain(
    paths: Sequence[Path], *, protocol: Mapping[str, Any]
) -> tuple[dict[str, Any], ...]:
    """Load and validate a genesis-to-immediate-predecessor chain."""

    chain: list[dict[str, Any]] = []
    for index, path in enumerate(paths):
        value, _ = _read_json(path, f"predecessor bundle[{index}]")
        current = _validate_bundle_value(
            value,
            protocol=protocol,
            predecessor_chain=tuple(chain) if chain else None,
        )
        chain.append(current)
    return tuple(chain)


def load_protocol(path: os.PathLike[str] | str) -> tuple[dict[str, Any], str]:
    """Load, schema-check, and freeze a protocol, returning its raw SHA-256."""

    value, raw = _read_json(path, "protocol")
    normalized = _validate_protocol_value(value)
    return normalized, hashlib.sha256(raw).hexdigest()


def load_bundle(
    path: os.PathLike[str] | str,
    *,
    protocol: Mapping[str, Any],
    predecessor_path: os.PathLike[str] | str | None = None,
    predecessor_paths: Sequence[os.PathLike[str] | str] | None = None,
) -> dict[str, Any]:
    """Load a bundle and prove its protocol and predecessor bindings."""

    frozen = _validate_protocol_value(protocol)
    chain_paths = _normalize_predecessor_paths(predecessor_path, predecessor_paths)
    value, _ = _read_json(path, "bundle")
    chain = _load_predecessor_chain(chain_paths, protocol=frozen)
    return _validate_bundle_value(
        value,
        protocol=frozen,
        predecessor_chain=chain or None,
    )


def _canonical_json_pretty(value: Any) -> bytes:
    _scan_value(value)
    try:
        body = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        return (body + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        _fail("serialization_error", f"cannot serialize JSON: {exc.__class__.__name__}")


def _atomic_write(path: Path, content: bytes, *, check: bool, label: str) -> dict[str, Any]:
    if len(content) > MAX_FILE_BYTES:
        _fail("size_limit", f"{label} exceeds {MAX_FILE_BYTES} bytes")
    target = _assert_output_path(path, label, create_parent=not check)
    digest = hashlib.sha256(content).hexdigest()
    if check:
        if not target.exists():
            _fail("output_missing", f"{label} is missing in check mode")
        _assert_regular_file(target, label, max_bytes=MAX_FILE_BYTES)
        try:
            existing = target.read_bytes()
        except OSError as exc:
            _fail("file_unreadable", f"{label} cannot be read: {exc.__class__.__name__}")
        if existing != content:
            _fail("output_drift", f"{label} bytes differ in check mode")
        return {"status": "checked", "check": True, "materialized": False, "sha256": digest}

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o644)
        if target.is_symlink():
            _fail("unsafe_symlink", f"{label} became a symlink")
        os.replace(temporary, target)
        temporary = None
    except CoevolutionBundleError:
        raise
    except OSError as exc:
        _fail("atomic_write", f"cannot materialize {label}: {exc.__class__.__name__}")
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass
    return {"status": "materialized", "check": False, "materialized": True, "sha256": digest}


def write_json_atomic(
    path: os.PathLike[str] | str,
    value: Any,
    *,
    check: bool = False,
) -> dict[str, Any]:
    """Write canonical pretty JSON or check exact byte equality."""

    return _atomic_write(
        _as_path(path, "JSON output"),
        _canonical_json_pretty(value),
        check=check,
        label="JSON output",
    )


def write_text_atomic(
    path: os.PathLike[str] | str,
    value: str,
    *,
    check: bool = False,
) -> dict[str, Any]:
    """Write UTF-8 report text atomically or check exact byte equality."""

    if not isinstance(value, str):
        _fail("invalid_type", "text output must be a string")
    if "\x00" in value:
        _fail("unsafe_reference", "text output contains NUL")
    text = value if value.endswith("\n") else value + "\n"
    try:
        content = text.encode("utf-8")
    except UnicodeEncodeError:
        _fail("invalid_utf8", "text output contains invalid Unicode")
    return _atomic_write(_as_path(path, "text output"), content, check=check, label="text output")


def materialize_bundle(
    protocol_path: os.PathLike[str] | str,
    output_path: os.PathLike[str] | str,
    bundle: Mapping[str, Any],
    *,
    predecessor_path: os.PathLike[str] | str | None = None,
    predecessor_paths: Sequence[os.PathLike[str] | str] | None = None,
    check: bool = False,
) -> dict[str, Any]:
    """Revalidate a bundle against a protocol and atomically materialize it."""

    protocol, protocol_raw_sha256 = load_protocol(protocol_path)
    output = _as_path(output_path, "bundle output")
    input_paths = [_as_path(protocol_path, "protocol")]
    chain_paths = _normalize_predecessor_paths(predecessor_path, predecessor_paths)
    input_paths.extend(chain_paths)
    _assert_distinct_output(output, input_paths, "bundle output")
    chain = _load_predecessor_chain(chain_paths, protocol=protocol)
    normalized = _validate_bundle_value(
        bundle,
        protocol=protocol,
        predecessor_chain=chain or None,
    )
    content = _canonical_json_pretty(normalized)
    result = _atomic_write(output, content, check=check, label="bundle output")
    result.update(
        {
            "bundle_id": normalized["bundle_id"],
            "bundle_hash": normalized["bundle_hash"],
            "protocol_id": protocol["protocol_id"],
            "protocol_hash": normalized["protocol_hash"],
            "protocol_raw_sha256": protocol_raw_sha256,
        }
    )
    return result


def check_bundle(
    protocol_path: os.PathLike[str] | str,
    bundle_path: os.PathLike[str] | str,
    *,
    predecessor_path: os.PathLike[str] | str | None = None,
    predecessor_paths: Sequence[os.PathLike[str] | str] | None = None,
) -> dict[str, Any]:
    """Return the core's descriptive projection for a validated bundle."""

    protocol, _ = load_protocol(protocol_path)
    bundle = load_bundle(
        bundle_path,
        protocol=protocol,
        predecessor_path=predecessor_path,
        predecessor_paths=predecessor_paths,
    )
    chain = _load_predecessor_chain(
        _normalize_predecessor_paths(predecessor_path, predecessor_paths),
        protocol=protocol,
    )
    return _core_call(
        core.project_bundle,
        bundle,
        protocol=protocol,
        predecessor_chain=chain or None,
    )


def _request_value(value: Any) -> dict[str, Any]:
    _scan_value(value, "rescore request")
    if not isinstance(value, Mapping):
        _fail("invalid_type", "rescore request must be an object")
    unknown = sorted(set(value) - _REQUEST_FIELDS)
    if unknown:
        _fail("unknown_field", f"rescore request contains unknown field(s): {', '.join(unknown)}")
    missing = sorted(_REQUEST_REQUIRED - set(value))
    if missing:
        _fail("missing_field", f"rescore request missing required field(s): {', '.join(missing)}")
    evaluator = value["evaluator_release"]
    score = value["score_payload"]
    if not isinstance(evaluator, Mapping):
        _fail("invalid_type", "rescore request.evaluator_release must be an object")
    if not isinstance(score, Mapping):
        _fail("invalid_type", "rescore request.score_payload must be an object")
    actor = value.get("actor")
    if actor is not None and (not isinstance(actor, str) or not actor.strip()):
        _fail("invalid_type", "rescore request.actor must be a non-empty string or null")
    normalized: dict[str, Any] = {
        "evaluator_release": dict(evaluator),
        "score_payload": dict(score),
        "actor": actor,
        "retained_surfaces": value.get("retained_surfaces", ()),
        "required_surfaces": value.get("required_surfaces", ()),
        "changes": value.get("changes", ()),
        "deterministic_code": value.get("deterministic_code", False),
    }
    for key in ("retained_surfaces", "required_surfaces", "changes"):
        items = normalized[key]
        if not isinstance(items, Sequence) or isinstance(items, (str, bytes, bytearray)):
            _fail("invalid_type", f"rescore request.{key} must be an array")
        if len(items) > MAX_ARRAY_ITEMS:
            _fail("array_limit", f"rescore request.{key} exceeds {MAX_ARRAY_ITEMS} items")
        normalized[key] = [
            item
            if isinstance(item, str)
            else _fail("invalid_type", f"rescore request.{key} must contain strings")
            for item in items
        ]
    if not isinstance(normalized["deterministic_code"], bool):
        _fail("invalid_type", "rescore request.deterministic_code must be a boolean")
    return normalized


def append_rescore_files(
    protocol_path: os.PathLike[str] | str,
    bundle_path: os.PathLike[str] | str,
    request_path: os.PathLike[str] | str,
    output_path: os.PathLike[str] | str,
    *,
    predecessor_path: os.PathLike[str] | str | None = None,
    predecessor_paths: Sequence[os.PathLike[str] | str] | None = None,
    check: bool = False,
) -> dict[str, Any]:
    """Append a data-only rescore request and materialize a validated successor."""

    protocol, protocol_raw_sha256 = load_protocol(protocol_path)
    output = _as_path(output_path, "rescore output")
    bundle_input = _as_path(bundle_path, "bundle")
    request_input = _as_path(request_path, "rescore request")
    chain_paths = _normalize_predecessor_paths(predecessor_path, predecessor_paths)
    _assert_distinct_output(
        output,
        [
            _as_path(protocol_path, "protocol"),
            bundle_input,
            request_input,
            *chain_paths,
        ],
        "rescore output",
    )
    original = load_bundle(
        bundle_path,
        protocol=protocol,
        predecessor_paths=chain_paths,
    )
    predecessor_chain = _load_predecessor_chain(chain_paths, protocol=protocol)
    _, original_raw = _read_json(bundle_path, "bundle")
    request_value, _ = _read_json(request_path, "rescore request", max_bytes=MAX_REQUEST_BYTES)
    request = _request_value(request_value)
    successor = _core_call(
        core.append_rescore,
        original,
        request["evaluator_release"],
        request["score_payload"],
        actor=request["actor"],
        retained_surfaces=request["retained_surfaces"],
        required_surfaces=request["required_surfaces"],
        changes=request["changes"],
        deterministic_code=request["deterministic_code"],
        protocol=protocol,
        predecessor_chain=predecessor_chain or None,
    )
    # A data-only operation must leave the source bytes untouched and retain a
    # byte-for-byte predecessor prefix in the resulting ledger.
    _, current_raw = _read_json(bundle_path, "bundle")
    if current_raw != original_raw:
        _fail("input_mutated", "bundle input changed during rescore")
    result = materialize_bundle(
        protocol_path,
        output,
        successor,
        predecessor_paths=(*chain_paths, bundle_input),
        check=check,
    )
    result.update(
        {
            "successor": successor,
            "protocol_raw_sha256": protocol_raw_sha256,
            "input_sha256": hashlib.sha256(original_raw).hexdigest(),
        }
    )
    return result


_REPORT_METRICS = (
    "false_promotion_share",
    "invalid_candidate_promotion_rate",
    "useful_candidate_power",
    "exploit_acceptance",
    "critical_failure",
    "bridge_reversal",
    "taint",
    "missingness",
    "quarantine",
    "optional_stopping",
    "revocation_completeness",
)

_MAX_REPORT_CONTRASTS = 15

_REPORT_DEFINITIONS = (
    (
        "false_promotion_share",
        "invalid promotions (null, harmful, or adversarial) / all candidate promotions",
    ),
    (
        "invalid_candidate_promotion_rate",
        "invalid promotions (null, harmful, or adversarial) / invalid candidate opportunities",
    ),
    ("useful_candidate_power", "useful promotions / useful candidate opportunities"),
    ("exploit_acceptance", "accepted exploits / exploit candidates"),
    ("critical_failure", "critical failures / task disposition attempts"),
    ("bridge_reversal", "later bridge reversals / passed bridge replicates"),
    ("taint", "tainted task disposition attempts / task disposition attempts"),
    ("missingness", "missing task dispositions / task disposition attempts"),
    ("quarantine", "quarantined task dispositions / task disposition attempts"),
    (
        "optional_stopping",
        "optional-stopping events / eligible optional-stopping replicates",
    ),
    ("revocation_completeness", "complete descendants / declared descendants"),
)


def _render_scalar(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value, allow_nan=False, sort_keys=True)
    if isinstance(value, str):
        return value
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")
        )
    except (TypeError, ValueError):
        return "unknown"


def render_bundle_report(
    protocol: Mapping[str, Any],
    bundle: Mapping[str, Any],
    projection: Mapping[str, Any],
    *,
    predecessor_path: os.PathLike[str] | str | None = None,
    predecessor_paths: Sequence[os.PathLike[str] | str] | None = None,
) -> str:
    """Render a deterministic, descriptive report (never an authority claim)."""

    frozen = _validate_protocol_value(protocol)
    chain_paths = _normalize_predecessor_paths(predecessor_path, predecessor_paths)
    chain = _load_predecessor_chain(chain_paths, protocol=frozen)
    normalized = _validate_bundle_value(
        bundle,
        protocol=frozen,
        predecessor_chain=chain or None,
    )
    if not isinstance(projection, Mapping):
        _fail("invalid_type", "projection must be an object")
    _scan_value(projection, "projection")
    derived = _core_call(
        core.project_bundle,
        normalized,
        protocol=frozen,
        predecessor_chain=chain or None,
    )
    # The caller-supplied projection is an untrusted view. Never use it to
    # invent metrics, and never recursively harvest arbitrary ledger keys.
    # Operating metrics come only from the internally recomputed core
    # projection. Core emits an empty mapping when the dependency-bound
    # simulation seal is absent, revoked, tainted, or unscorable.
    projected_metrics = derived.get("operating_metrics", {})
    operating_metrics = projected_metrics if isinstance(projected_metrics, Mapping) else {}
    summary_metrics_available = bool(operating_metrics)
    projected_endpoints = derived.get("primary_endpoints", {})
    primary_endpoints = projected_endpoints if isinstance(projected_endpoints, Mapping) else {}
    if any(not isinstance(endpoint, Mapping) for endpoint in primary_endpoints.values()):
        primary_endpoints = {}
    projected_contrasts = derived.get("contrast_diagnostics", ())
    contrast_diagnostics = (
        projected_contrasts
        if isinstance(projected_contrasts, Sequence)
        and not isinstance(projected_contrasts, (str, bytes, bytearray))
        else ()
    )

    records = normalized["records"]

    lines = [
        "# AEL-CEP trajectory bundle report",
        "",
        "Status: synthetic / provisional / no-effect Stage 0.",
        "Scope: descriptive projection only; this report is not authority and does not establish real-world validity, superiority, safety, custody, transfer, or promotion.",
        "",
        f"Protocol: `{frozen['protocol_id']}`",
        f"Epoch: `{frozen['epoch']['epoch_id']}`",
        f"Bundle: `{normalized['bundle_id']}`",
        f"Bundle hash: `{normalized['bundle_hash']}`",
        "",
        "## Counts",
        "",
        f"- Records: {len(records)}",
        f"- Score runs: {sum(1 for record in records if record['record_type'] == 'score_run')}",
        f"- Latest score keys: {len(derived.get('latest_scores', {}))}",
        f"- Tainted records: {len(derived.get('tainted_record_ids', ()))}",
        f"- Revoked records: {len(derived.get('revoked_record_ids', ()))}",
        f"- Unscorable records: {len(derived.get('unscorable_record_ids', ()))}",
        "",
        "## Operating-characteristic metrics",
        "",
    ]
    if not summary_metrics_available:
        lines.append(
            "- Current operating metrics: unavailable (summary absent, revoked, tainted, or unscorable)."
        )
    for metric in _REPORT_METRICS:
        lines.append(f"- `{metric}`: {_render_scalar(operating_metrics.get(metric))}")
    lines.extend(
        [
            "",
            "Definitions (core-derived count / denominator units):",
            "",
        ]
    )
    lines.extend(f"- `{metric}`: {definition}." for metric, definition in _REPORT_DEFINITIONS)
    lines.extend(
        [
            "",
            "## Primary prospective endpoints",
            "",
        ]
    )
    if not primary_endpoints:
        lines.append(
            "- Primary endpoints: unavailable (summary absent, revoked, tainted, or unscorable)."
        )
    else:
        for arm in sorted(primary_endpoints):
            endpoint = primary_endpoints[arm]
            sum_ppm = endpoint.get("sum_ppm")
            observed_count = endpoint.get("observed_count")
            mean_ppm = endpoint.get("mean_ppm")
            lines.append(
                f"- `{arm}`: {_render_scalar({'sum_ppm': sum_ppm, 'observed_count': observed_count, 'mean_ppm': mean_ppm})}"
            )
    lines.extend(
        [
            "",
            "## Contrast diagnostics",
            "",
        ]
    )
    if not contrast_diagnostics:
        lines.append(
            "- Contrast diagnostics: unavailable (summary absent, revoked, tainted, or unscorable)."
        )
    else:
        status_counts = {
            status: sum(
                1
                for item in contrast_diagnostics
                if isinstance(item, Mapping) and item.get("status") == status
            )
            for status in ("causal_eligible", "diagnostic_only", "not_estimable")
        }
        lines.append(
            "- Eligibility counts: "
            + ", ".join(f"{status}={count}" for status, count in status_counts.items())
        )
        ordered_contrasts = sorted(
            (item for item in contrast_diagnostics if isinstance(item, Mapping)),
            key=lambda item: str(item.get("contrast_id", "")),
        )
        for item in ordered_contrasts[:_MAX_REPORT_CONTRASTS]:
            lines.append(
                f"- {_render_scalar({key: item.get(key) for key in ('contrast_id', 'status', 'reason', 'endpoint_delta_ppm')})}"
            )
        omitted = len(ordered_contrasts) - _MAX_REPORT_CONTRASTS
        if omitted > 0:
            lines.append(
                f"- Additional diagnostics omitted: {omitted} (report limit {_MAX_REPORT_CONTRASTS})."
            )
    lines.extend(
        [
            "",
            "Interpretation boundary: synthetic operating characteristics and contrast diagnostics are provisional, descriptive, and non-claiming; ppm values are integer parts per million and do not establish causal validity, and missing values remain unknown rather than zero.",
            "",
        ]
    )
    return "\n".join(lines)


# The first released AEL-CEP contract is CLI/file/schema only.  Direct imports
# remain available to repository-owned tooling but are experimental internals,
# so star imports intentionally expose no compatibility-bearing surface.
__all__: tuple[str, ...] = ()
