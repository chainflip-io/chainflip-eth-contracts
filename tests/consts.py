from crypto import *
from utils import *


ZERO_ADDR = "0000000000000000000000000000000000000000"
ETH_ADDR = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
TEST_AMNT = 10**17
# Notable the only part of the hash involved in CREATE2 that has padding
SWAP_ID_HEX = cleanHexStrPad(12345)
JUNK_INT = 1234


# Keys for use in tests

# Original keys in the constructor
AGG_PRIV_HEX_1 = "fbcb47bc85b881e0dfb31c872d4e06848f80530ccbd18fc016a27c4a744d0eba"
AGG_K_HEX_1 = "d51e13c68bf56155a83e50fd9bc840e2a1847fb9b49cd206a577ecd1cd15e285"
AGG_SIGNER_1 = Signer(AGG_PRIV_HEX_1, AGG_K_HEX_1)

GOV_PRIV_HEX_1 = "fd0491a72700b50de61ea97c81a2df9d5a301e9b5e71d5c7786ee86d1994f1b8"
GOV_K_HEX_1 = "41e581ebb25e4d7f7bd9c502e45389ac0b991fe27052e6d9e78521d06a0eeca1"
GOV_SIGNER_1 = Signer(GOV_PRIV_HEX_1, GOV_K_HEX_1)

# New keys
AGG_PRIV_HEX_2 = "bbade2da39cfc81b1b64b6a2d66531ed74dd01803dc5b376ce7ad548bbe23608"
AGG_K_HEX_2 = "ecb77b2eb59614237e5646b38bdf03cbdbdce61c874fdee6e228edaa26f01f5d"
AGG_SIGNER_2 = Signer(AGG_PRIV_HEX_2, AGG_K_HEX_2)

GOV_PRIV_HEX_2 = "6b357e74e81bd16c202e6406d0e1883f758f0495973f316be323daebec04ad85"
GOV_K_HEX_2 = "699d69410c7ae51703a515ae0c186889a47e0fda1f661b8451f90ec5d780eb4b"
GOV_SIGNER_2 = Signer(GOV_PRIV_HEX_2, GOV_K_HEX_2)


# Revert messages
# Vault
REV_MSG_NZ_UINT = "Vault: uint input is empty"
REV_MSG_NZ_ADDR = "Vault: address input is empty"
REV_MSG_NZ_BYTES32 = "Vault: bytes32 input is empty"

# Validate
REV_MSG_MSGHASH = "Vault: invalid msgHash"
REV_MSG_SIG = "Vault: Sig invalid"


REV_MSG_PUB_KEY_X = "Public-key x >= HALF_Q"
REV_MSG_SIG_LESS_Q = "Sig must be reduced modulo Q"
REV_MSG_INPUTS_0 = "No zero inputs allowed"