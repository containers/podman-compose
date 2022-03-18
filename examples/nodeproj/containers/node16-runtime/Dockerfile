FROM registry.fedoraproject.org/fedora-minimal:35
ARG NODE_VER=16
# microdnf -y module enable nodejs:${NODE_VER}
RUN \
  echo -e "[nodejs]\nname=nodejs\nstream=${NODE_VER}\nprofiles=\nstate=enabled\n" > /etc/dnf/modules.d/nodejs.module && \
  microdnf -y install shadow-utils nodejs zopfli findutils busybox && \
  microdnf clean all
RUN adduser -d /app app && mkdir -p /app/code/.home && chown app:app -R /app/code && chmod 711 /app /app/code/.home && usermod -d /app/code/.home app
ENV XDG_CONFIG_HOME=/app/code/.home
ENV HOME=/app/code/.home
WORKDIR /app/code

