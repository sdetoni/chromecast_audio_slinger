FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    smbclient \
    cifs-utils \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone https://github.com/sdetoni/chromecast_audio_slinger .

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Create config symlink
RUN mkdir -p /config \
    && if [ -d /app/config ]; then mv /app/config /app/config.dist; fi \
    && ln -s /config /app/config

# create pi user
RUN useradd -m -u 1000 -s /bin/bash pi

# Copy entrypoint
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

VOLUME ["/config"]

# switch user
USER pi

ENTRYPOINT ["/entrypoint.sh"]
