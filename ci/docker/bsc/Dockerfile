FROM ghcr.io/bnb-chain/bsc:1.6.7

USER root
RUN rm -rf /geth/data && mkdir -p /geth/data

# Copy custom config
COPY genesis.json /genesis.json
COPY password.txt /password.txt
COPY config.toml /config.toml
COPY nodekey /geth/nodekey
COPY bls /geth/data/bls
COPY keystore /geth/data/keystore
COPY --chmod=755 entrypoint.sh /entrypoint.sh

# Run initialisation
RUN geth init --datadir /geth/data /genesis.json

WORKDIR /

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD geth --datadir /geth/data attach --exec eth.blockNumber

ENTRYPOINT ["/entrypoint.sh"]
