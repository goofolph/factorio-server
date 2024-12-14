FROM debian:bookworm-slim

RUN apt update && apt install -y xz-utils vim && apt clean && rm -rf /var/lib/apt/lists/*
COPY factorio-headless_linux*.tar.xz /tmp/factorio-headless_linux.tar.xz
RUN tar xf /tmp/factorio-headless_linux.tar.xz -C /opt/ && rm /tmp/factorio-headless_linux.tar.xz

WORKDIR /opt/factorio

EXPOSE 34197/udp 27015/tcp

VOLUME /factorio

CMD /opt/factorio/bin/x64/factorio --start-server /factorio/saves/$SAVE_NAME --server-settings /factorio/config/$SERVER_SETTINGS
