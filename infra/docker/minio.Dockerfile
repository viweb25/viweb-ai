# Development only: upstream no longer publishes the Docker Hub image.
# Review storage maintenance/licensing before production or customer distribution.
FROM golang:1.24.8-bookworm AS build
ARG MINIO_RELEASE=RELEASE.2025-10-15T17-29-55Z
RUN git clone --depth 1 --branch "$MINIO_RELEASE" https://github.com/minio/minio.git /src
WORKDIR /src
RUN CGO_ENABLED=0 go build -trimpath -o /out/minio .

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --no-create-home minio \
    && mkdir /data && chown minio:minio /data
COPY --from=build /out/minio /usr/local/bin/minio
USER minio
ENTRYPOINT ["minio"]
