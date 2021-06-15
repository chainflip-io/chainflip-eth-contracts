from consts import *
from brownie import reverts


def test_verifySignature_rev_pubKeyX(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[0] += Signer.HALF_Q_INT

    with reverts(REV_MSG_PUB_KEY_X):
        schnorrTest.testVerifySignature(*sigData[:2], *signerPubData)


def test_verifySignature_rev_SigLessQ(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)
    sigData[1] = Signer.Q_INT

    with reverts(REV_MSG_SIG_LESS_Q):
        schnorrTest.testVerifySignature(*sigData[:2], *AGG_SIGNER_1.getPubData())


def test_verifySignature_rev_nonceTimesGeneratorAddress_zero(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[2] = ZERO_ADDR_PACKED

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(*sigData[:2], *signerPubData)


def test_verifySignature_rev_signingPubKeyX_zero(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(*sigData[:2], *signerPubData)


def test_verifySignature_rev_signature_zero(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)
    sigData[1] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(*sigData[:2], *AGG_SIGNER_1.getPubData())


def test_verifySignature_rev_msgHash_zero(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)
    sigData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(*sigData[:2], *AGG_SIGNER_1.getPubData())