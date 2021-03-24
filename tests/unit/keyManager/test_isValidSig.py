from consts import *
from brownie import reverts
from shared_tests import *



def test_isValidSig(cf):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)
    tx = cf.keyManager.isValidSig(sigData, cleanHexStr(sigData[0]), KEYID_TO_NUM[AGG])
    
    assert tx.return_value == True
    txTimeTest(cf.keyManager.getLastValidateTime(), cf.keyManager.tx)


def test_isValidSig_rev_msgHash(cf):
    # Fails because msgHash in sigData is a hash of JUNK_HEX, whereas JUNK_HEX
    # is used directly for contractMsgHash
    with reverts(REV_MSG_MSGHASH):
        cf.keyManager.isValidSig(AGG_SIGNER_1.getSigData(JUNK_HEX), JUNK_HEX, KEYID_TO_NUM[AGG])


def test_isValidSig_rev_sig(cf):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)
    sigData[1] = JUNK_INT
    with reverts(REV_MSG_SIG):
        cf.keyManager.isValidSig(sigData, cleanHexStr(sigData[0]), KEYID_TO_NUM[AGG])
