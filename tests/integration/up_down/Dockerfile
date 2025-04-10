FROM docker.io/library/debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y \
        dumb-init \
    && apt-get autoremove
RUN mkdir -p /mnt/test/
