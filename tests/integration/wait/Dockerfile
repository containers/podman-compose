FROM docker.io/library/debian:bookworm-slim
RUN apt-get update && \
    apt-get install -y \
        dumb-init && \
    apt-get autoremove
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT [ "/entrypoint.sh" ]
