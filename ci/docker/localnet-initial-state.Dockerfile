FROM debian:bullseye
ARG INITIAL_STATE_DIR
ARG BUILD_DATETIME
ARG VCS_REF

LABEL org.opencontainers.image.authors="dev@chainflip.io"
LABEL org.opencontainers.image.vendor="Chainflip Labs GmbH"
LABEL org.opencontainers.image.title="chainflip/localnet-initial-state"
LABEL org.opencontainers.image.source="https://github.com/chainflip-io/chainflip-eth-contracts/blob/${VCS_REF}/ci/docker/localnet-initial-state.Dockerfile"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.created="${BUILD_DATETIME}"
LABEL org.opencontainers.image.environment="development"
LABEL org.opencontainers.image.documentation="https://github.com/chainflip-io/chainflip-eth-contracts"

WORKDIR /initial-state
COPY ${INITIAL_STATE_DIR} /initial-state

WORKDIR /initial-state
