FROM python:3.14-alpine

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock /app/

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY load_monitor.py /app/load_monitor.py

# Expose the webhook port
EXPOSE 5000

# Run the application
CMD ["uv", "run", "load_monitor.py"]
