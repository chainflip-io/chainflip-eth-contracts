from consts import *
from brownie import reverts


MSG_HASH_HEX = "18f224412c876d8efb2a3fa670837b5ad1347120363c2b310653f610d382729b"

def test_verifySignature(a, schnorrSECP256K1):
    assert schnorrSECP256K1.verifySignature(*AGG_SIGNER_1.getSigData(MSG_HASH_HEX), *AGG_SIGNER_1.getPubData())


def test_verifySignature_rev_pubKeyX(a, schnorrSECP256K1):
    signerPubData = list(AGG_SIGNER_1.getPubData())
    signerPubData[0] += Signer.HALF_Q_INT

    with reverts(REV_MSG_PUB_KEY_X):
        schnorrSECP256K1.verifySignature(*AGG_SIGNER_1.getSigData(MSG_HASH_HEX), *signerPubData)


def test_verifySignature_rev_SigLessQ(a, schnorrSECP256K1):
    sigData = list(AGG_SIGNER_1.getSigData(MSG_HASH_HEX))
    sigData[1] = Signer.Q_INT

    with reverts(REV_MSG_SIG_LESS_Q):
        schnorrSECP256K1.verifySignature(*sigData, *AGG_SIGNER_1.getPubData())


def test_verifySignature_rev_nonceTimesGeneratorAddress_zero(a, schnorrSECP256K1):
    signerPubData = list(AGG_SIGNER_1.getPubData())
    signerPubData[2] = ZERO_ADDR

    with reverts(REV_MSG_INPUTS_0):
        schnorrSECP256K1.verifySignature(*AGG_SIGNER_1.getSigData(MSG_HASH_HEX), *signerPubData)


def test_verifySignature_rev_signingPubKeyX_zero(a, schnorrSECP256K1):
    signerPubData = list(AGG_SIGNER_1.getPubData())
    signerPubData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrSECP256K1.verifySignature(*AGG_SIGNER_1.getSigData(MSG_HASH_HEX), *signerPubData)


def test_verifySignature_rev_signature_zero(a, schnorrSECP256K1):
    sigData = list(AGG_SIGNER_1.getSigData(MSG_HASH_HEX))
    sigData[1] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrSECP256K1.verifySignature(*sigData, *AGG_SIGNER_1.getPubData())


def test_verifySignature_rev_msgHash_zero(a, schnorrSECP256K1):
    sigData = list(AGG_SIGNER_1.getSigData(MSG_HASH_HEX))
    sigData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrSECP256K1.verifySignature(*sigData, *AGG_SIGNER_1.getPubData())
