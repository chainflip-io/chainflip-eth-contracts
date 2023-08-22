from crypto import *
from utils import *

# -----Networks-----
eth_localnet = 10997
eth_goerli = 5
eth_sepolia = 11155111
eth_mainnet = 1
arb_localnet = 412346
arb_testnet = 421613
arb_mainnet = 42161
hardhat = 31337
arbitrum_networks = [arb_localnet, arb_testnet, arb_mainnet]

# -----General/shared-----
ZERO_ADDR_PACKED = "0000000000000000000000000000000000000000"
ZERO_ADDR = "0x" + ZERO_ADDR_PACKED
NATIVE_ADDR = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
NON_ZERO_ADDR = "0x0000000000000000000000000000000000000001"
E_18 = 10**18
TEST_AMNT = 10**17
ONE_NATIVE = E_18
JUNK_INT = 42069
JUNK_HEX = web3.toHex(JUNK_INT)
# Notable the only part of the hash involved in CREATE2 that has padding
JUNK_HEX_PAD = cleanHexStrPad(JUNK_HEX)
AGG = "Agg"
INIT_TOKEN_SUPPLY = int(10**8 * E_18)
INIT_NATIVE_BAL = int(10000 * E_18)
SECS_PER_BLOCK = 13
# USDC and USDT use 6 decimals
INIT_USDC_SUPPLY = int(20 * 10**6 * 10**6)
INIT_USDC_ACCOUNT = int(10**6 * 10**6)
TEST_AMNT_USDC = int(10**6)

# Time in seconds
MINUTE = 60
HOUR = 60 * 60
DAY = HOUR * 24
MONTH = 30 * DAY
YEAR = 365 * DAY
QUARTER_YEAR = int(YEAR / 4)

# -----Shared-----
REV_MSG_NZ_UINT = "Shared: uint input is empty"
REV_MSG_NZ_ADDR = "Shared: address input is empty"
REV_MSG_NZ_BYTES32 = "Shared: bytes32 input is empty"
REV_MSG_NZ_PUBKEYX = "Shared: pubKeyX is empty"

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
nonces = {AGG: 0}


# Deployed contract might have already signed some messages, so we need to sync the nonce
# of the contract with the nonces in consts.py used to signed the messages.
def syncNonce(keyManager):
    while keyManager.isNonceUsedByAggKey(nonces[AGG]) != False:
        nonces[AGG] += 1

    print("Synched Nonce: ", nonces[AGG])
    return nonces


# Keys for use in tests

# Original keys in the constructor
AGG_PRIV_HEX_1 = "fbcb47bc85b881e0dfb31c872d4e06848f80530ccbd18fc016a27c4a744d0eba"
AGG_SIGNER_1 = Signer(AGG_PRIV_HEX_1, AGG, nonces)

# New keys
AGG_PRIV_HEX_2 = "bbade2da39cfc81b1b64b6a2d66531ed74dd01803dc5b376ce7ad548bbe23608"
AGG_SIGNER_2 = Signer(AGG_PRIV_HEX_2, AGG, nonces)

NULL_KEY = (0, 0)
BAD_AGG_KEY = [0xEE2E4DC8797847D69A9E59C1B051E3EF2ABD7A60AA7EDC3100A69666DF9AC525, 0x01]

# consumeKeyNonce
REV_MSG_SIG = "KeyManager: Sig invalid"
REV_MSG_KEYMANAGER_NONCE = "KeyManager: nonce already used"
# modifiers
REV_MSG_DELAY = "KeyManager: not enough time"
REV_MSG_KEYMANAGER_GOVERNOR = "KeyManager: not governor"
REV_MSG_KEYMANAGER_NOT_COMMUNITY = "KeyManager: not Community Key"

# -----SchnorrSECP256K1-----
REV_MSG_PUB_KEY_X = "Public-key x >= HALF_Q"
REV_MSG_SIG_LESS_Q = "Sig must be reduced modulo Q"
REV_MSG_INPUTS_0 = "No zero inputs allowed"


# -----FLIP-----
INIT_SUPPLY = 9 * 10**7 * E_18
REV_MSG_FLIP_ISSUER = "FLIP: not issuer"

REV_MSG_ERC20_EXCEED_BAL = "ERC20: transfer amount exceeds balance"
REV_MSG_ERC20_INSUF_ALLOW = "ERC20: insufficient allowance"
REV_MSG_INTEGER_OVERFLOW = "Integer overflow"
REV_MSG_BURN_BALANCE = "ERC20: burn amount exceeds balance"

# -----StateChainGateway-----
NUM_GENESIS_VALIDATORS = 5
GENESIS_STAKE = 50000 * E_18
GATEWAY_INITIAL_BALANCE = NUM_GENESIS_VALIDATORS * GENESIS_STAKE
NEW_TOTAL_SUPPLY_MINT = (10 * 10**7) * E_18
NEW_TOTAL_SUPPLY_BURN = (8 * 10**7) * E_18
MIN_FUNDING = 1 * E_18
MAX_TEST_FUND = 1 * 10**7 * E_18

# 13292
REDEMPTION_DELAY = 2 * DAY
REDEMPTION_DELAY_TESTNETS = 2 * MINUTE
NULL_CLAIM = (0, ZERO_ADDR, 0, 0, ZERO_ADDR)

REV_MSG_MIN_FUNDING = "Gateway: not enough funds"
REV_MSG_CLAIM_EXISTS = "Gateway: a pending redemption exists"
REV_MSG_EXPIRY_TOO_SOON = "Gateway: expiry time too soon"
REV_MSG_NOT_ON_TIME = "Gateway: early or already execd"
REV_MSG_FLIP_ADDRESS = "Gateway: Flip address already set"
REV_MSG_OLD_FLIP_SUPPLY_UPDATE = "Gateway: old FLIP supply update"
REV_MSG_NOT_FLIP = "Gateway: wrong FLIP ref"
REV_MSG_NOT_EXECUTOR = "Gateway: not executor"

# -----Vault-----
AGG_KEY_EMERGENCY_TIMEOUT = 3 * 24 * 60 * 60
REV_MSG_VAULT_DELAY = "Vault: not enough time"
REV_MSG_INSUFFICIENT_GAS = "Vault: insufficient gas"

# -----GovernanceCommunityGuarded-----
REV_MSG_GOV_ENABLED_GUARD = "Governance: community guard enabled"
REV_MSG_GOV_DISABLED_GUARD = "Governance: community guard disabled"
REV_MSG_GOV_NOT_COMMUNITY = "Governance: not Community Key"
REV_MSG_GOV_GOVERNOR = "Governance: not governor"
REV_MSG_GOV_SUSPENDED = "Governance: suspended"
REV_MSG_GOV_NOT_SUSPENDED = "Governance: not suspended"

# -----Vesting-----
BENEF_TRANSF = True
BENEF_NON_TRANSF = False
REV_MSG_NO_TOKENS = "Vesting: no tokens are due"
REV_MSG_NOT_REVOKER = "Vesting: not the revoker"
REV_MSG_VESTING_EXPIRED = "Vesting: vesting expired"
REV_MSG_NOT_BENEFICIARY = "Vesting: not the beneficiary"
REV_MSG_BENEF_NOT_TRANSF = "Vesting: beneficiary not transferrable"
REV_MSG_CLIFF_AFTER_END = "Vesting: cliff_ after end_"
REV_MSG_INVALID_FINAL_TIME = "Vesting: final time is before current time"
REV_MSG_TOKEN_REVOKED = "Vesting: token revoked"
REV_MSG_SCGREF_REV_GOV = "AddrHolder: not the governor"


# -----CFReceiver-----
REV_MSG_CFREC_REVERTED = "CFReceiverFail: call reverted"
REV_MSG_CFREC_SENDER = "CFReceiver: caller not Chainflip sender"
