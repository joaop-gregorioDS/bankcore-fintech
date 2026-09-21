FROM docker:27-dind-rootless

# This image is only a disposable P6-F2 target. It is intentionally not a
# BankCore runtime image and is never published to a registry.
USER root
RUN apk add --no-cache ansible-core bash py3-cryptography sudo && \
    sed -i 's#^rootless:x:1000:1000:Rootless:/home/rootless:/bin/sh#bankcore:x:1000:1000:BankCore:/home/bankcore:/bin/bash#' /etc/passwd && \
    sed -i 's/^rootless:/bankcore:/' /etc/group /etc/subuid /etc/subgid && \
    mv /home/rootless /home/bankcore && \
    chown -R 1000:1000 /home/bankcore && \
    printf '%s\n' 'root ALL=(ALL) NOPASSWD: ALL' 'bankcore ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/bankcore && \
    chmod 0440 /etc/sudoers.d/bankcore && \
    printf '%s\n' '[safe]' '    directory = /workspace' > /etc/gitconfig

USER bankcore
ENV HOME=/home/bankcore \
    XDG_RUNTIME_DIR=/run/user/1000 \
    DOCKER_TLS_CERTDIR=""
