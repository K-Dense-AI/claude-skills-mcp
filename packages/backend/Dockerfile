# Dockerfile for Claude Skills MCP Backend
# Optimized for production deployment with CPU-only PyTorch

FROM python:3.12-slim

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy backend source
COPY packages/backend /app/backend
COPY config.example.json /app/

# Install backend package
RUN cd /app/backend && uv pip install --system .

# Expose default port
EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

# Run backend server
# Default: local access (127.0.0.1)
# For remote access, override with: --host 0.0.0.0
ENTRYPOINT ["claude-skills-mcp-backend"]
CMD ["--host", "0.0.0.0", "--port", "8765"]

