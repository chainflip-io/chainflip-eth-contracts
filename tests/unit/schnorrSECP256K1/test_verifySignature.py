from consts import *
from brownie import reverts


def test_verifySignature_rev_pubKeyX(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[0] += Signer.HALF_Q_INT

    with reverts(REV_MSG_PUB_KEY_X):
        schnorrTest.testVerifySignature(*sigData[:2], *signerPubData, sigData[3])


def test_verifySignature_rev_SigLessQ(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD)
    sigData[1] = Signer.Q_INT

    with reverts(REV_MSG_SIG_LESS_Q):
        schnorrTest.testVerifySignature(*sigData[:2], *AGG_SIGNER_1.getPubData(), sigData[3])


def test_verifySignature_rev_nonceTimesGeneratorAddress_zero(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD)

    signerPubData = AGG_SIGNER_1.getPubData()

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(*sigData[:2], *signerPubData, ZERO_ADDR)


def test_verifySignature_rev_signingPubKeyX_zero(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(*sigData[:2], *signerPubData, sigData[3])


def test_verifySignature_rev_signature_zero(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD)
    sigData[1] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(*sigData[:2], *AGG_SIGNER_1.getPubData(), sigData[3])


def test_verifySignature_rev_msgHash_zero(schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD)
    sigData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(*sigData[:2], *AGG_SIGNER_1.getPubData(), sigData[3])