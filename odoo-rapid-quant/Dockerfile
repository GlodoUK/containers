FROM ghcr.io/glodouk/containers/psql:17.8
ARG RQ_VERSION=v0.1.0
RUN apk add --no-cache curl tar bash file
WORKDIR /app
RUN curl -fsSL "https://github.com/GlodoUK/odoo-rapid-quant/releases/download/${RQ_VERSION}/odoo-rapid-quant-${RQ_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    | tar -xz && \
    chmod +x odoo-rapid-quant
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
