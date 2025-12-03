# renovate: datasource=docker depName=alpine versioning=docker
ARG ALPINE_VERSION=3.23

FROM alpine:${ALPINE_VERSION}
ARG KUBECTL_VERSION=v1.34.1

RUN apk add --no-cache bash curl coreutils
RUN curl -LO "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl" && \
    curl -LO "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl.sha256"

RUN echo "$(cat kubectl.sha256) kubectl" | sha256sum --check && \
    chmod a+x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl && \
    rm kubectl.sha256 && \
    adduser -u 1000 --disabled-password kubectl

USER kubectl
ENTRYPOINT [ "kubectl" ]
CMD [ "--help" ]
