# Use a multi-platform base image with newer Rust version
FROM --platform=$TARGETPLATFORM rust:1.81-alpine AS builder
WORKDIR /usr/src/app
COPY . .
# Install build dependencies
RUN apk add --no-cache \
    musl-dev \
    gcc \
    pkgconfig \
    openssl-dev

RUN cargo build --release

FROM --platform=$TARGETPLATFORM alpine:latest
COPY --from=builder /usr/src/app/target/release/decentralized-ai-agents /usr/local/bin/
ENV RUST_LOG=info
EXPOSE 8080
CMD ["decentralized-ai-agents"]
