import sys
from eth_abi import encode_abi
from web3 import Web3 as web3

import consts
from utils import cleanHexStr
from crypto import Signer

n = len(sys.argv)
if n != 4:
    print(f"Invalid usage. Format is {sys.argv[0]} message key nonce")
    exit()

message = sys.argv[1]
key = sys.argv[2]
nonces = {"Agg": int(sys.argv[3])}

signer = Signer(key, "Agg", nonces)

[s, nonceTimesGeneratorAddress] = signer.sign(message)


print("0x" + encode_abi(['uint256', 'address'], [s, nonceTimesGeneratorAddress]).hex(), end="")

