FROM python:3.12-slim

RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin agent
WORKDIR /workspace

# The sandbox image contains only test/runtime tooling for the current MVP.
# Customer repositories will move to per-stack images selected by a policy layer.
RUN pip install --no-cache-dir \
    pytest==8.4.1 \
    fastapi==0.116.1 \
    uvicorn==0.35.0 \
    pydantic==2.11.7 \
    httpx==0.28.1

USER 1000:1000
ENV HOME=/home/agent \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

CMD ["python", "-m", "pytest", "-q"]
