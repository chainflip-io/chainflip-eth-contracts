FROM node:18

ARG BUILD_DATETIME
ARG BACKEND_REF
ARG VCS_REF

ENV ARB_RAW_TXS_FILE=/app/arbRawDeploymentTxs.json

LABEL org.opencontainers.image.authors="dev@chainflip.io"
LABEL org.opencontainers.image.vendor="Chainflip Labs GmbH"
LABEL org.opencontainers.image.title="chainflip/arbitrum-gizmo-shop"
LABEL org.opencontainers.image.source="https://github.com/chainflip-io/chainflip-eth-contracts/blob/${VCS_REF}/ci/docker/arbitrum-gizmo-shop.Dockerfile"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.created="${BUILD_DATETIME}"
LABEL org.opencontainers.image.environment="${BACKEND_REF}"
LABEL org.opencontainers.image.backend_ref="development"
LABEL org.opencontainers.image.documentation="https://github.com/chainflip-io/chainflip-eth-contracts"

# Create app directory
WORKDIR /app

# Install app dependencies
COPY ./arb-utils/package.json /app/package.json
COPY ./arb-utils/pnpm-lock.yaml /app/pnpm-lock.yaml

RUN npm install -g pnpm
RUN pnpm install

# Add Script
COPY ./arb-utils/arb_init.ts /app/arb_init.ts

# Add ARB raw TXs JSON
COPY ./scripts/.artefacts/arbRawDeploymentTxs.json /app/arbRawDeploymentTxs.json

CMD ["pnpm", "tsx", "/app/arb_init.ts"]
