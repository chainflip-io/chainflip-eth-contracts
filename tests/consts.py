from crypto import *
from utils import *


ETH_ADDR = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
TEST_AMNT = 10**17
# Notable the only part of the hash involved in CREATE2 that has padding
SWAP_ID_HEX = cleanHexStrPad(12345)


# Keys for use in tests

# Original keys in the constructor
AGG_PRIV_HEX_1 = "5d18fc9fb6494384932af3bda6fe8102c0fa7a26774e22af3993a69e2ca79565"
AGG_K_HEX_1 = "d51e13c68bf56155a83e50fd9bc840e2a1847fb9b49cd206a577ecd1cd15e285"
AGG_SIGNER_1 = Signer(AGG_PRIV_HEX_1, AGG_K_HEX_1)

GOV_PRIV_HEX_1 = "3e119a16f829514901aea610834d80604cd8d206defdec8abbe8a5458135c2ad"
GOV_K_HEX_1 = "41e581ebb25e4d7f7bd9c502e45389ac0b991fe27052e6d9e78521d06a0eeca1"
GOV_SIGNER_1 = Signer(GOV_PRIV_HEX_1, GOV_K_HEX_1)

# New keys
AGG_PRIV_HEX_2 = "a29a4fb46ccde60da8abd6f2b67079b377a3f7ee435e9874fb47f44604ae3adb"
AGG_K_HEX_2 = "ecb77b2eb59614237e5646b38bdf03cbdbdce61c874fdee6e228edaa26f01f5d"
AGG_SIGNER_2 = Signer(AGG_PRIV_HEX_2, AGG_K_HEX_2)

GOV_PRIV_HEX_2 = "7aea54539a61ca038844a0e0dba9fe71814a22cacbfc798ed03fd9795628f210"
GOV_K_HEX_2 = "699d69410c7ae51703a515ae0c186889a47e0fda1f661b8451f90ec5d780eb4b"
GOV_SIGNER_2 = Signer(GOV_PRIV_HEX_2, GOV_K_HEX_2)