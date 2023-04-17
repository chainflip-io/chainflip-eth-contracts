from consts import *
from brownie import reverts
from brownie.test import given, strategy


@given(
    st_address=strategy("address", exclude=0),
    st_sig=strategy("uint256", exclude=0),
)
def test_verifySignature(schnorrTest, st_address, st_sig):
    sigData = AGG_SIGNER_1.generate_sigData(JUNK_HEX_PAD, nonces)

    if st_sig != sigData[0] or st_address != sigData[2]:
        schnorrTest.testVerifySignature(
            JUNK_INT, st_sig, *AGG_SIGNER_1.getPubData(), st_address
        )

    schnorrTest.testVerifySignature(
        JUNK_INT, sigData[0], *AGG_SIGNER_1.getPubData(), sigData[2]
    )


def test_verifySignature_rev_pubKeyX(schnorrTest):
    sigData = AGG_SIGNER_1.generate_sigData(JUNK_HEX_PAD, nonces)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[0] += Signer.HALF_Q_INT

    print(REV_MSG_PUB_KEY_X)

    with reverts(REV_MSG_PUB_KEY_X):
        schnorrTest.testVerifySignature(
            JUNK_INT, sigData[0], *signerPubData, sigData[2]
        )


def test_verifySignature_rev_SigLessQ(schnorrTest):
    sigData = AGG_SIGNER_1.generate_sigData(JUNK_HEX_PAD, nonces)
    sigData[0] = Signer.Q_INT

    with reverts(REV_MSG_SIG_LESS_Q):
        schnorrTest.testVerifySignature(
            JUNK_INT, sigData[0], *AGG_SIGNER_1.getPubData(), sigData[2]
        )


def test_verifySignature_rev_nonceTimesGeneratorAddress_zero(schnorrTest):
    sigData = AGG_SIGNER_1.generate_sigData(JUNK_HEX_PAD, nonces)

    signerPubData = AGG_SIGNER_1.getPubData()

    print(JUNK_INT, sigData[0], *signerPubData, ZERO_ADDR)

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(JUNK_INT, sigData[0], *signerPubData, ZERO_ADDR)


def test_verifySignature_rev_signingPubKeyX_zero(schnorrTest):
    sigData = AGG_SIGNER_1.generate_sigData(JUNK_HEX_PAD, nonces)

    signerPubData = AGG_SIGNER_1.getPubData()
    signerPubData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(
            JUNK_INT, sigData[0], *signerPubData, sigData[2]
        )


def test_verifySignature_rev_signature_zero(schnorrTest):
    sigData = AGG_SIGNER_1.generate_sigData(JUNK_HEX_PAD, nonces)
    sigData[0] = 0

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(
            JUNK_INT, sigData[0], *AGG_SIGNER_1.getPubData(), sigData[2]
        )


def test_verifySignature_rev_msgHash_zero(schnorrTest):
    sigData = AGG_SIGNER_1.generate_sigData(JUNK_HEX_PAD, nonces)

    with reverts(REV_MSG_INPUTS_0):
        schnorrTest.testVerifySignature(
            0, sigData[0], *AGG_SIGNER_1.getPubData(), sigData[2]
        )
