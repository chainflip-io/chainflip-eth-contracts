from crypto import *
from utils import *

# -----General/shared-----
ZERO_ADDR_PACKED = "0000000000000000000000000000000000000000"
ZERO_ADDR = "0x" + ZERO_ADDR_PACKED
ETH_ADDR = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
NON_ZERO_ADDR = "0x0000000000000000000000000000000000000001"
TEST_AMNT = 10**17
ONE_ETH = 10**18
JUNK_INT = 12345
JUNK_HEX = web3.toHex(JUNK_INT)
# Notable the only part of the hash involved in CREATE2 that has padding
JUNK_HEX_PAD = cleanHexStrPad(JUNK_HEX)
E_18 = 10**18
AGG = "Agg"
GOV = "Gov"
KEYID_TO_NUM  = {AGG: 0, GOV: 1}
NUM_TO_KEYID  = [AGG, GOV]
INIT_TOKEN_SUPPLY = int(10**26)
INIT_ETH_BAL = 10000 * E_18
SECS_PER_BLOCK = 13

# Time in seconds
HOUR = 60 * 60
DAY = HOUR * 24


REV_MSG_NZ_UINT = "Shared: uint input is empty"
REV_MSG_NZ_ADDR = "Shared: address input is empty"
REV_MSG_NZ_BYTES32 = "Shared: bytes32 input is empty"


# -----KeyManager-----
# 2 days
AGG_KEY_TIMEOUT = 2 * 24 * 60 * 60

# Technically these aren't constants - it would be good to have them be part of the
# Signer class, but since there are multiple agg keys/signers, and the same for gov,
# they need to somehow share state so that multiple versions of agg signer/key don't
# both start from 0 because they will collide and cause the 2nd one to fail, since
# the nonce is specific to the agg key and gov key in general, regardless of what the
# specific pubkey etc of the key is. It's not possible to have the state reset upon a
# new agg key because the current design uses a mapping that tracks every nonce ever.
# This wouldn't be the case if a single uint was used to track the current nonce for
# each agg and gov key tho
nonces = {AGG: 0, GOV: 0}
def agg_null_sig(): return (0, 0, nonces[AGG], ZERO_ADDR)
def gov_null_sig(): return (0, 0, nonces[GOV], ZERO_ADDR)

REV_MSG_DELAY = "KeyManager: not enough delay"

# Keys for use in tests

# Original keys in the constructor
AGG_PRIV_HEX_1 = "fbcb47bc85b881e0dfb31c872d4e06848f80530ccbd18fc016a27c4a744d0eba"
AGG_K_HEX_1 = "d51e13c68bf56155a83e50fd9bc840e2a1847fb9b49cd206a577ecd1cd15e285"
AGG_SIGNER_1 = Signer(AGG_PRIV_HEX_1, AGG_K_HEX_1, AGG, nonces)

GOV_PRIV_HEX_1 = "fd0491a72700b50de61ea97c81a2df9d5a301e9b5e71d5c7786ee86d1994f1b8"
GOV_K_HEX_1 = "41e581ebb25e4d7f7bd9c502e45389ac0b991fe27052e6d9e78521d06a0eeca1"
GOV_SIGNER_1 = Signer(GOV_PRIV_HEX_1, GOV_K_HEX_1, GOV, nonces)

# New keys
AGG_PRIV_HEX_2 = "bbade2da39cfc81b1b64b6a2d66531ed74dd01803dc5b376ce7ad548bbe23608"
AGG_K_HEX_2 = "ecb77b2eb59614237e5646b38bdf03cbdbdce61c874fdee6e228edaa26f01f5d"
AGG_SIGNER_2 = Signer(AGG_PRIV_HEX_2, AGG_K_HEX_2, AGG, nonces)

GOV_PRIV_HEX_2 = "6b357e74e81bd16c202e6406d0e1883f758f0495973f316be323daebec04ad85"
GOV_K_HEX_2 = "699d69410c7ae51703a515ae0c186889a47e0fda1f661b8451f90ec5d780eb4b"
GOV_SIGNER_2 = Signer(GOV_PRIV_HEX_2, GOV_K_HEX_2, GOV, nonces)

NULL_KEY = (0, 0, ZERO_ADDR)

# nzKey
REV_MSG_PUBKEYX = "Shared: pubKeyX is empty"
REV_MSG_NONCETIMESGADDR = "Shared: nonceTimesGAddr is empty"
REV_MSG_NONCETIMESGADDR_EMPTY = "No zero inputs allowed"

# isValidSig
REV_MSG_MSGHASH = "KeyManager: invalid msgHash"
REV_MSG_SIG = "KeyManager: Sig invalid"

# SchnorrSECP256K1
REV_MSG_PUB_KEY_X = "Public-key x >= HALF_Q"
REV_MSG_SIG_LESS_Q = "Sig must be reduced modulo Q"
REV_MSG_INPUTS_0 = "No zero inputs allowed"


# -----FLIP-----
INIT_SUPPLY = (9 * 10**7) * E_18

REV_MSG_ERC20_EXCEED_BAL = "ERC20: transfer amount exceeds balance"
REV_MSG_ERC777_EXCEED_BAL = "ERC777: transfer amount exceeds balance"
REV_MSG_INTEGER_OVERFLOW = "Integer overflow"


# -----StakeManager-----
NUM_GENESIS_VALIDATORS = 5
GENESIS_STAKE = 50000 * E_18
STAKEMANAGER_INITIAL_BALANCE = NUM_GENESIS_VALIDATORS * GENESIS_STAKE
NEW_TOTAL_SUPPLY_MINT = (10 * 10**7) * E_18
NEW_TOTAL_SUPPLY_BURN = (8 * 10**7) * E_18
MIN_STAKE = 40000 * E_18
MAX_TEST_STAKE = INIT_SUPPLY / 9
# 13292
CLAIM_DELAY = 2 * DAY
NULL_CLAIM = (0, ZERO_ADDR, 0, 0)

REV_MSG_MIN_STAKE = "StakeMan: stake too small"
REV_MSG_NO_FISH = "StakeMan: something smells fishy"
REV_MSG_SM_ARR_LEN = "StakeMan: arrays not same length"
REV_MSG_CLAIM_EXISTS = "StakeMan: a pending claim exists"
REV_MSG_EXPIRY_TOO_SOON = "StakeMan: expiry time too soon"
REV_MSG_NOT_ON_TIME = "StakeMan: early, late, or execd"
REV_MSG_OLD_FLIP_SUPPLY_UPDATE = "StakeMan: old FLIP supply update"


# -----Vault-----
REV_MSG_V_ARR_LEN = "Vault: arrays not same length"
REV_MSG_SENDER = "Vault: only Vault can send ETH"