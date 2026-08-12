FROM python@sha256:6771159cd4fa5d9bba1258caf0b82e6b73458c694d178ad97c5e925c2d0e1a91

LABEL org.opencontainers.image.title="Kizz AEL allowlist proxy"
LABEL org.opencontainers.image.description="CONNECT-only egress boundary for isolated model runners"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY proxy.py /usr/local/lib/ael/proxy.py

USER 65532:65532
ENTRYPOINT ["python", "/usr/local/lib/ael/proxy.py"]

