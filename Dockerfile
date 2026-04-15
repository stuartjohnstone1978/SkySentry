FROM python:3.11-slim

# Create a non-privileged user
RUN groupadd -r sentrygroup && useradd -r -g sentrygroup sentryuser

WORKDIR /app

# Install dependencies as root
RUN pip install --no-cache-dir requests python-dotenv ollama

# Copy code and change ownership to our new user
COPY --chown=sentryuser:sentrygroup . .

# Switch to the non-privileged user
USER sentryuser

CMD ["python", "observer_aviation.py"]