FROM python:3.12-slim

WORKDIR /workspace

# Install uv
RUN pip install uv

# Copy workspace config
COPY pyproject.toml uv.lock* ./
COPY packages/ packages/
COPY apps/api/ apps/api/

# Install dependencies
RUN uv sync --frozen 2>/dev/null || uv sync

WORKDIR /workspace/apps/api

EXPOSE 8080
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
