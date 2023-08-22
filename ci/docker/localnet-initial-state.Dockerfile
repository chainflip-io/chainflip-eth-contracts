FROM debian:bullseye
ARG BUILD_DATETIME
ARG BACKEND_REF
ARG VCS_REF

LABEL org.opencontainers.image.authors="dev@chainflip.io"
LABEL org.opencontainers.image.vendor="Chainflip Labs GmbH"
LABEL org.opencontainers.image.title="chainflip/localnet-initial-state"
LABEL org.opencontainers.image.source="https://github.com/chainflip-io/chainflip-eth-contracts/blob/${VCS_REF}/ci/docker/localnet-initial-state.Dockerfile"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.created="${BUILD_DATETIME}"
LABEL org.opencontainers.image.environment="${BACKEND_REF}"
LABEL org.opencontainers.image.backend_ref="development"
LABEL org.opencontainers.image.documentation="https://github.com/chainflip-io/chainflip-eth-contracts"

WORKDIR /initial-state

COPY localnet-initial-state /initial-state

RUN ls -laR /initial-state

WORKDIR /initial-state
