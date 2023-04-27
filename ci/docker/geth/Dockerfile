FROM ethereum/client-go:v1.11.6-amd64

# Delete default configuration
RUN rm -rf /root/data /geth/data

# Copy custom config
COPY genesis.json /geth/genesis.json
COPY geth_password /geth/password

# Run initialisation
RUN echo "3d0a95697e9c3ee59b57142bafc5eacaf9b6263c4854b6fedcddefad6bb89b27" > /geth/key.prv
RUN geth account import --datadir /geth/data --password /geth/password /geth/key.prv
RUN geth init --datadir /geth/data /geth/genesis.json

WORKDIR /geth

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD geth attach --exec eth.blockNumber

# Hardcode the full command
ENTRYPOINT geth \
        --http.api=admin,db,debug,eth,miner,net,personal,shh,txpool,web3 \
        --miner.etherbase=0xa994738936572Fb88564d69134F67Aaa7C7d4A6E \
        --unlock=0xa994738936572Fb88564d69134F67Aaa7C7d4A6E \
        --rpc.allow-unprotected-txs \
        --password=/geth/password \
        --ws.api=web3,eth,debug \
        --allow-insecure-unlock \
        --datadir=/geth/data \
        --http.corsdomain=* \
        --http.addr=0.0.0.0 \
        --ws.addr=0.0.0.0 \
        --miner.threads=1 \
        --networkid=10997 \
        --http.port=8545 \
        --http.vhosts=* \
        --ws.origins=* \
        --ws.port=8546 \
        --gcmode=archive \
        --nodiscover \
        --http \
        --mine \
        --ws

