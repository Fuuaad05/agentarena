FROM python:3.11-slim
RUN pip install --no-cache-dir pytest==9.1.1 pytest-json-report==1.5.0
WORKDIR /workspace
CMD ["python", "-m", "pytest", "-q"]
