FROM python:3.15-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# The bot writes .env and data/, which are bind-mounted from the host. Running
# as root meant those writes depended on CAP_DAC_OVERRIDE, so the container
# could not drop its capabilities without silently losing the ability to save
# YOUTUBE_LAST_VIDEO_ID. Running as the uid that owns them on the host needs no
# capabilities at all. Override at build time if your host account differs:
#   docker compose build --build-arg APP_UID=$(id -u) --build-arg APP_GID=$(id -g)
ARG APP_UID=1001
ARG APP_GID=1001

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Created after COPY so the application files stay root-owned and read-only to
# the bot: it has no reason to rewrite its own code.
RUN groupadd --gid "$APP_GID" app \
    && useradd --uid "$APP_UID" --gid "$APP_GID" --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/data \
    && chown "$APP_UID:$APP_GID" /app/data

# config.py creates DATA_DIR when it is imported. Under compose a bind mount
# already provides it, but the bare image has to work too: CI imports the bot in
# a container with nothing mounted, and a non-root user cannot mkdir inside
# root-owned /app. Hence creating and chowning it here.

USER app

# Run the bot (which also starts the Flask keep-alive server)
CMD ["python", "bot.py"]
