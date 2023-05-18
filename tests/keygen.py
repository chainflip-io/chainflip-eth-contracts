from eth_abi import encode_abi
import secrets
from crypto import Signer

pk = secrets.token_hex(32)

signer = Signer(pk, "Agg", 0)

pubkeyx = int(signer.pubKeyX.hex(), 16)
pubkeyypar = int(signer.pubKeyYParHex)

# ABI-encode the output
abi_encoded = encode_abi(['uint256', 'uint256', 'uint8'], [int(pk, 16), pubkeyx, pubkeyypar]).hex()
# Make sure that it doesn't print a newline character
print("0x" + abi_encoded, end="")
