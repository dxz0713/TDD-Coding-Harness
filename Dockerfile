FROM python:3.12-slim

WORKDIR /workspace

# Copy pyproject.toml and source code
COPY pyproject.toml .
COPY src/ src/

# Install dependencies and project
RUN pip install --no-cache-dir -e ".[dev]"

ENTRYPOINT ["tdd-harness"]
CMD ["--help"]