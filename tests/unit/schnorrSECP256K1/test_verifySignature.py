from consts import *
from brownie import reverts


def test_verifySignature_rev_pubKeyX(cf, schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cf.keyManager.address)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[0] += Signer.HALF_Q_INT

    print(REV_MSG_PUB_KEY_X)

    with reverts(REV_MSG_PUB_KEY_X):
        schnorrTest.testVerifySignature(*sigData[2:4], *signerPubData, sigData[5])


def test_verifySignature_rev_SigLessQ(cf, schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
    sigData[3] = Signer.Q_INT

    with reverts(REV_MSG_SIG_LESS_Q):
        schnorrTest.testVerifySignature(
            *sigData[2:4], *AGG_SIGNER_1.getPubData(), sigData[5]
        )


def test_verifySignature_rev_nonceTimesGeneratorAddress_zero(cf, schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cf.keyManager.address)

    signerPubData = AGG_SIGNER_1.getPubData()

    print(*sigData[2:4], *signerPubData, ZERO_ADDR)

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(*sigData[2:4], *signerPubData, ZERO_ADDR)


def test_verifySignature_rev_signingPubKeyX_zero(cf, schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cf.keyManager.address)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(*sigData[2:4], *signerPubData, sigData[5])


def test_verifySignature_rev_signature_zero(cf, schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
    sigData[3] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(
            *sigData[2:4], *AGG_SIGNER_1.getPubData(), sigData[5]
        )


def test_verifySignature_rev_msgHash_zero(cf, schnorrTest):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
    sigData[2] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(
            *sigData[2:4], *AGG_SIGNER_1.getPubData(), sigData[5]
        )
