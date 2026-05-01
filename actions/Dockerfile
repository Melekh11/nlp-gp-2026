FROM rasa/rasa-sdk:3.6.2
COPY requirements.txt /app/requirements.txt
USER root
RUN /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt
USER 1001
