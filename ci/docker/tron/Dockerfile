FROM tronprotocol/java-tron

# Copy both TRON node configuration files so the image can be used
# as either witness node (default) or observer peer (by overriding CMD).
COPY config.conf /tron/config/config.conf
COPY config-peer.conf /tron/config/config-peer.conf
# Place logback.xml in the java-tron working directory (/java-tron) so it is on the
# classpath as a fallback, and also point to it explicitly via JAVA_TOOL_OPTIONS so the
# JVM picks it up regardless of classpath ordering.
# JAVA_TOOL_OPTIONS is read automatically by any JVM process, no entrypoint changes needed.
COPY logback.xml /java-tron/logback.xml
ENV JAVA_TOOL_OPTIONS="-Dlogback.configurationFile=/java-tron/logback.xml"

HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=30s \
    CMD curl -s -X POST -H "Content-Type: application/json" http://127.0.0.1:8090/wallet/getnowblock

# Default: start as witness/block-producer node.
# Witness private key corresponds to keys/bashful/eth_private_key_file:
#   EVM:  0x076d3803349fd5FB48863c5Fc33483cB2243C0Df
#   TRON: TAeUa4FzpoveH7UUArvfXdeS3TmXiWU1ds
CMD ["-c", "/tron/config/config.conf", "-d", "/tron/output-directory", "-w", "-p", "ef895dc87b545ba42ece3162b8441f712c892d0681ae34682eeb3e5443afefaa"]
