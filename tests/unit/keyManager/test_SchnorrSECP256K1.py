from consts import *
from brownie import reverts


def test_verifySignature_rev_pubKeyX(a, cf):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[0] += Signer.HALF_Q_INT

    with reverts(REV_MSG_PUB_KEY_X):
        cf.keyManager.isValidSig(cleanHexStr(sigData[0]), sigData, signerPubData)


def test_verifySignature_rev_SigLessQ(a, cf):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)
    sigData[1] = Signer.Q_INT

    with reverts(REV_MSG_SIG_LESS_Q):
        cf.keyManager.isValidSig(cleanHexStr(sigData[0]), sigData, AGG_SIGNER_1.getPubData())


def test_verifySignature_rev_nonceTimesGeneratorAddress_zero(a, cf):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[2] = ZERO_ADDR_PACKED

    with reverts(REV_MSG_INPUTS_0):
        cf.keyManager.isValidSig(cleanHexStr(sigData[0]), sigData, signerPubData)


def test_verifySignature_rev_signingPubKeyX_zero(a, cf):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        cf.keyManager.isValidSig(cleanHexStr(sigData[0]), sigData, signerPubData)


def test_verifySignature_rev_signature_zero(a, cf):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)
    sigData[1] = 0

    with reverts(REV_MSG_INPUTS_0):
        cf.keyManager.isValidSig(cleanHexStr(sigData[0]), sigData, AGG_SIGNER_1.getPubData())


def test_verifySignature_rev_msgHash_zero(a, cf):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX)
    sigData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        cf.keyManager.isValidSig(cleanHexStr(sigData[0]), sigData, AGG_SIGNER_1.getPubData())
