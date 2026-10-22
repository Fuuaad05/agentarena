FROM python:3.11-slim

RUN pip install --no-cache-dir \
    pytest \
    pytest-json-report

WORKDIR /workspace

CMD ["python", "-m", "pytest", "-q"]