from consts import *
from brownie import reverts
from shared_tests import *


# For testing validate, we'll just use fetchDeposit since it doesn't
# require anything to happen beforehand

# There's not really anything that can be asserted when validate is
# valid other than _lastValidateTime
def test_validate(vault):
    # Unfortunately we can't define callDataSig in this general file even though
    # all tests use the same initiall calldata because vault isn't known
    # outside fcns
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, SWAP_ID_HEX, ETH_ADDR)
    vault.fetchDeposit(*AGG_SIGNER_1.getSigData(callDataNoSig), SWAP_ID_HEX, ETH_ADDR)

    txTimeTest(vault.getLastValidateTime(), vault.tx)


def test_validate_rev_msgHash(vault):
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, SWAP_ID_HEX, ETH_ADDR)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[0] = JUNK_INT

    with reverts(REV_MSG_MSGHASH):
        vault.fetchDeposit(*sigData, SWAP_ID_HEX, ETH_ADDR)


def test_validate_rev_sig(vault):
    callDataNoSig = vault.fetchDeposit.encode_input(0, 0, SWAP_ID_HEX, ETH_ADDR)
    sigData = AGG_SIGNER_1.getSigData(callDataNoSig)
    sigData[1] = JUNK_INT

    with reverts(REV_MSG_SIG):
        vault.fetchDeposit(*sigData, SWAP_ID_HEX, ETH_ADDR)
