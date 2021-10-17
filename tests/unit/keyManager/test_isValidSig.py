from consts import *
from brownie import reverts
from shared_tests import *


def test_isValidSig(cfAW):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD)
    tx = cfAW.keyManager.isUpdatedValidSig(sigData, cleanHexStr(sigData[0]), KEYID_TO_NUM[AGG])

    assert tx.return_value == True


def test_isValidSig_rev_msgHash(cfAW):
    # Fails because msgHash in sigData is a hash of JUNK_HEX_PAD, whereas JUNK_HEX_PAD
    # is used directly for contractMsgHash
    with reverts(REV_MSG_MSGHASH):
        cfAW.keyManager.isUpdatedValidSig(AGG_SIGNER_1.getSigData(JUNK_HEX_PAD), JUNK_HEX_PAD, KEYID_TO_NUM[AGG])


def test_isValidSig_rev_sig(cfAW):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD)
    sigData[1] = JUNK_HEX
    with reverts(REV_MSG_SIG):
        cfAW.keyManager.isUpdatedValidSig(sigData, cleanHexStr(sigData[0]), KEYID_TO_NUM[AGG])


def test_isValidSig_check_all(a, cf):
    whitelisted = [cf.vault, cf.keyManager, cf.stakeManager]
    for addr in whitelisted + list(a):
        if addr in whitelisted:
            sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD)
            tx = cf.keyManager.isUpdatedValidSig(sigData, cleanHexStr(sigData[0]), KEYID_TO_NUM[AGG], {'from': addr})
            assert tx.return_value == True
        else:
            with reverts(REV_MSG_WHITELIST):
