FROM node@sha256:3638d9a6fe4030bd716be989438248074489337ba3275657f93595428be4fc03

ARG CODEX_VERSION=0.146.0

RUN apt-get update \
    && apt-get install --yes --no-install-recommends bash ca-certificates git python3 ripgrep \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global "@openai/codex@${CODEX_VERSION}" \
    && codex --version

LABEL org.opencontainers.image.title="Kizz AEL Codex runner"
LABEL org.opencontainers.image.description="Pinned Codex CLI runtime for isolated AEL studies"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY entrypoint.py /usr/local/lib/ael/entrypoint.py

USER 65532:65532
ENTRYPOINT ["python3", "/usr/local/lib/ael/entrypoint.py"]
