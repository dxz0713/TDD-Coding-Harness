FROM python:3.12-slim

WORKDIR /app

# Install harness
COPY pyproject.toml /app/
COPY src/ /app/src/
RUN pip install --no-cache-dir -e ".[dev]"

# Install webui deps
COPY webui/requirements.txt /app/webui/
RUN pip install --no-cache-dir -r /app/webui/requirements.txt

COPY webui/ /app/webui/

EXPOSE 8000
CMD ["uvicorn", "webui.app:app", "--host", "0.0.0.0", "--port", "8000"]