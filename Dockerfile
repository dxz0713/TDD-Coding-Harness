FROM python:3.12-slim

WORKDIR /workspace

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source code
COPY src/ src/

# Re-install with source
RUN pip install --no-cache-dir -e ".[dev]"

ENTRYPOINT ["tdd-harness"]
CMD ["--help"]