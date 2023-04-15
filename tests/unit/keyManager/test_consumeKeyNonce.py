from pprint import pprint
from consts import *
from brownie import reverts, chain
from shared_tests import *
from brownie.test import given, strategy
import pytest


@given(st_contractMsgHash=strategy("bytes32"), st_sender=strategy("address"))
def test_consumeKeyNonce(cf, st_contractMsgHash, st_sender):
    nonce = nonces[AGG]
    assert not cf.keyManager.isNonceUsedByAggKey(nonce)

    sigData = AGG_SIGNER_1.generate_sigData(
        Signer.generate_msgHash(
            st_contractMsgHash, nonces, cf.keyManager.address, st_sender
        ),
        nonces,
    )

    cf.keyManager.consumeKeyNonce(sigData, st_contractMsgHash, {"from": st_sender})

    assert cf.keyManager.isNonceUsedByAggKey(nonce, {"from": cf.ALICE})


@given(
    st_contractMsgHash=strategy("bytes32"),
    st_sender=strategy("address"),
    st_sig=strategy("uint256", exclude=0),
    st_kTimesGAddress=strategy("address"),
)
def test_consumeKeyNonce_rev_sig(
    cf, st_contractMsgHash, st_sender, st_sig, st_kTimesGAddress
):

    msgHash = Signer.generate_msgHash(JUNK_HEX, nonces, cf.keyManager.address, cf.ALICE)
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)

    if st_contractMsgHash != JUNK_HEX:
        with reverts(REV_MSG_SIG):
            cf.keyManager.consumeKeyNonce(
                sigData, st_contractMsgHash, {"from": cf.ALICE}
            )

    # Bruteforce the signature
    sigData_modif = sigData[:]
    sigData_modif[0] = st_sig
    with reverts(REV_MSG_SIG):
        cf.keyManager.consumeKeyNonce(sigData_modif, JUNK_HEX, {"from": cf.ALICE})

    # Bruteforce the kTimesGAddress
    sigData_modif = sigData[:]
    sigData_modif[2] = st_kTimesGAddress
    with reverts(REV_MSG_SIG):
        cf.keyManager.consumeKeyNonce(sigData_modif, JUNK_HEX, {"from": cf.ALICE})

    # Check that changing the nonce will fail. Seems like the hypothesis is smart
    # enough to figure this one out, so we add a check.
    if st_sig != sigData_modif[1]:
        sigData_modif = sigData[:]
        sigData_modif[1] = st_sig
        with reverts(REV_MSG_SIG):
            cf.keyManager.consumeKeyNonce(sigData_modif, JUNK_HEX, {"from": cf.ALICE})

    if st_sender != cf.ALICE:
        with reverts(REV_MSG_SIG):
            cf.keyManager.consumeKeyNonce(sigData, JUNK_HEX, {"from": st_sender})
    else:
        cf.keyManager.consumeKeyNonce(sigData, JUNK_HEX, {"from": st_sender})


# Check that signing the message for another chain won't pass verification
@given(
    st_contractMsgHash=strategy("bytes32"),
    st_sender=strategy("address"),
    st_chainID=strategy("uint256"),
)
def test_consumeKeyNonce_rev_chainID(cf, st_chainID, st_contractMsgHash, st_sender):

    sigData = AGG_SIGNER_1.generate_sigData(
        Signer.generate_msgHash(
            st_contractMsgHash,
            nonces,
            cf.keyManager.address,
            st_sender,
            chainId=st_chainID,
        ),
        nonces,
    )

    if st_chainID != chain.id:
        with reverts(REV_MSG_SIG):
            cf.keyManager.consumeKeyNonce(
                sigData, st_contractMsgHash, {"from": st_sender}
            )

    # Proof that it would pass verification with the right chainID
    sigData = AGG_SIGNER_1.generate_sigData(
        Signer.generate_msgHash(
            st_contractMsgHash,
            nonces,
            cf.keyManager.address,
            st_sender,
        ),
        nonces,
    )
    cf.keyManager.consumeKeyNonce(sigData, st_contractMsgHash, {"from": st_sender})


@given(st_contractMsgHash=strategy("bytes32"), st_sender=strategy("address"))
def test_consumeKeyNonce_rev_replay(cf, st_contractMsgHash, st_sender):
    nonce = nonces[AGG]
    assert not cf.keyManager.isNonceUsedByAggKey(nonce)

    sigData = AGG_SIGNER_1.generate_sigData(
        Signer.generate_msgHash(
            st_contractMsgHash, nonces, cf.keyManager.address, st_sender
        ),
        nonces,
    )

    cf.keyManager.consumeKeyNonce(sigData, st_contractMsgHash, {"from": st_sender})

    with reverts(REV_MSG_KEYMANAGER_NONCE):
        cf.keyManager.consumeKeyNonce(sigData, st_contractMsgHash, {"from": st_sender})
