FROM rasa/rasa:3.6.21

USER root

RUN python -m pip install --no-cache-dir \
    python-dotenv==1.1.0 \
    "pyngrok>=7.2,<8"

WORKDIR /app

COPY run_rasa.py /app/run_rasa.py

# docker-compose mounts the source code into /app, but keep the wrapper in the
# image too so the image remains usable without a bind mount.
ENTRYPOINT ["python", "/app/run_rasa.py"]
CMD ["--help"]
