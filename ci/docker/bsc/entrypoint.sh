#!/bin/sh
# FORK_TIME_1 and FORK_TIME_2 control when forks activate.
# During CI build, pass dynamic values (e.g. now+10, now+20) so forks
# activate shortly after the chain starts. For replay (committed image),
# leave unset so they default to 1, meaning all forks are already passed.
FORK_TIME_1=${FORK_TIME_1:-1}
FORK_TIME_2=${FORK_TIME_2:-1}
exec geth \
    --verbosity 4 \
    --config /config.toml \
    --datadir /geth/data \
    --nodekey /geth/nodekey \
    --rpc.allow-unprotected-txs \
    --allow-insecure-unlock \
    --ws --ws.addr 0.0.0.0 --ws.port 8545 \
    --http --http.addr 0.0.0.0 --http.port 8545 --http.corsdomain "*" \
    --metrics --metrics.addr localhost --metrics.port 6060 \
    --pprof --pprof.addr localhost --pprof.port 7060 \
    --gcmode full --syncmode full --monitor.maliciousvote \
    --rialtohash 0xb23274833b0bf0abeb4ba3ac140c80931b8e9aaeeba435940e053aa3ebd46e7c \
    --override.passedforktime $FORK_TIME_1 \
    --override.lorentz $FORK_TIME_1 \
    --override.maxwell $FORK_TIME_1 \
    --override.fermi $FORK_TIME_2 \
    --override.osaka $FORK_TIME_2 \
    --override.mendel $FORK_TIME_2 \
    --override.immutabilitythreshold 2048 \
    --override.breatheblockinterval 1200 \
    --override.minforblobrequest 576 \
    --override.defaultextrareserve 32 \
    --mine --vote \
    --unlock 0xbcdd0d2cda5f6423e57b6a4dcd75decbe31aecf0 \
    --miner.etherbase 0xbcdd0d2cda5f6423e57b6a4dcd75decbe31aecf0 \
    --password /password.txt \
    --blspassword /password.txt \
    2>&1
