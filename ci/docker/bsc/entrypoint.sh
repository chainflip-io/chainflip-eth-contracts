#!/bin/sh
NOW=$(date +%s)
T40=$((NOW + 40))
T50=$((NOW + 50))

exec geth \
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
    --override.passedforktime $T40 \
    --override.lorentz $T40 \
    --override.maxwell $T40 \
    --override.fermi $T50 \
    --override.osaka $T50 \
    --override.mendel $T50 \
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
