
FROM ethereum/client-go:alltools-v1.11.6-amd64

# Delete default configuration
RUN rm -rf /root/data /datadir

# Copy custom config
COPY genesis.json /datadir/genesis.json
COPY geth_password /datadir/passphrase

RUN mkdir -p /config
RUN mkdir -p /keystore

RUN chown -R 1000:1000 /config
RUN chown -R 1000:1000 /keystore

COPY --chown=1000:1000 accounts/0x3f1eae7d46d88f08fc2f8ed27fcb2ab183eb2d0e.json /keystore/0x3f1eae7d46d88f08fc2f8ed27fcb2ab183eb2d0e.key
COPY --chown=1000:1000 accounts/0x6a568afe0f82d34759347bb36f14a6bb171d2cbe.json /keystore/0x6a568afe0f82d34759347bb36f14a6bb171d2cbe.key
COPY --chown=1000:1000 accounts/0xe2148ee53c0755215df69b2616e552154edc584f.json /keystore/0xe2148ee53c0755215df69b2616e552154edc584f.key

# Run initialisation
RUN echo "b6b15c8cb491557369f3c7d2c287b053eb229daa9c22138887752191c9520659" > /0x3f1eae7d46d88f08fc2f8ed27fcb2ab183eb2d0e.prv
RUN geth account import --datadir /datadir --password /datadir/passphrase /0x3f1eae7d46d88f08fc2f8ed27fcb2ab183eb2d0e.prv
RUN geth init --datadir /datadir /datadir/genesis.json

WORKDIR /

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD geth --datadir /datadir attach --exec eth.blockNumber

# Hardcode the full command
ENTRYPOINT geth \
    --networkid=10997 \
    --http \
    --datadir=/datadir \
    --http.addr=0.0.0.0 \
    --authrpc.vhosts=* \
    --authrpc.port=8551 \
    --authrpc.addr=0.0.0.0 \
    --http.vhosts=* \
    --http.api=engine,personal,eth,net,web3 \
    --http.corsdomain=* \
    --ws \
    --ws.addr=0.0.0.0 \
    --ws.api=personal,eth,net,web3,debug,txpool \
    --allow-insecure-unlock \
    --unlock=0x3f1eae7d46d88f08fc2f8ed27fcb2ab183eb2d0e \
    --password=/datadir/passphrase \
    --authrpc.jwtsecret=/config/jwt.hex \
    --nodiscover \
    --syncmode=full \
    --mine \
    --miner.etherbase=0x3f1eae7d46d88f08fc2f8ed27fcb2ab183eb2d0e \
    --gcmode=archive \
    --override.shanghai=1
