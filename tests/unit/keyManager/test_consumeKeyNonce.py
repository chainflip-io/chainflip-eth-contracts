from pprint import pprint
from consts import *
from brownie import reverts, chain
from shared_tests import *
from brownie.test import given, strategy
import pytest


def test_consumeKeyNonce(cfAW):
    nonce = nonces[AGG]
    assert not cfAW.keyManager.isNonceUsedByAggKey(nonce)

    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cfAW.keyManager.address)
    tx = cfAW.keyManager.consumeKeyNonce(sigData, cleanHexStr(sigData[2]))

    assert nonce == sigData[4]
    assert cfAW.keyManager.isNonceUsedByAggKey(sigData[4])


def test_consumeKeyNonce_rev_msgHash(cfAW):
    # Fails because msgHash in sigData is a hash of JUNK_HEX_PAD, whereas JUNK_HEX_PAD
    # is used directly for contractMsgHash
    with reverts(REV_MSG_MSGHASH):
        cfAW.keyManager.consumeKeyNonce(
            AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cfAW.keyManager.address), JUNK_HEX_PAD
        )


def test_consumeKeyNonce_rev_sig(cfAW):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cfAW.keyManager.address)
    sigData[3] = JUNK_HEX
    with reverts(REV_MSG_SIG):
        cfAW.keyManager.consumeKeyNonce(sigData, cleanHexStr(sigData[2]))


@given(st_addr=strategy("address"))
def test_consumeKeyNonce_rev_keyManAddr(cfAW, st_addr):
    if st_addr != cfAW.keyManager:
        sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, st_addr)
        with reverts(REV_MSG_WRONG_KEYMANADDR):
            cfAW.keyManager.consumeKeyNonce(sigData, cleanHexStr(sigData[2]))


@given(st_chainID=strategy("uint256"))
def test_consumeKeyNonce_rev_chainID(cfAW, st_chainID):
    if st_chainID != chain.id:
        sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cfAW.keyManager.address)
        sigData[1] = st_chainID
        with reverts(REV_MSG_WRONG_CHAINID):
            cfAW.keyManager.consumeKeyNonce(sigData, cleanHexStr(sigData[2]))


# Transactions sent from non-EOA accounts breaks brownie coverage - skip coverage
@pytest.mark.skip_coverage
def test_consumeKeyNonce_check_all(a, cf):
    cf.whitelisted = [cf.vault, cf.keyManager, cf.stakeManager]
    for addr in cf.whitelisted + list(a):
        if addr in cf.whitelisted:
            sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
            cf.ALICE.transfer(to=addr, amount=ONE_ETH)
            cf.keyManager.consumeKeyNonce(
                sigData, cleanHexStr(sigData[2]), {"from": addr}
            )
        else:
            sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
            with reverts(REV_MSG_WHITELIST):
                cf.keyManager.consumeKeyNonce(sigData, cleanHexStr(sigData[2]))


# Split test_consumeKeyNonce_check in two because brownie coverage crashes when
# sending a transaction from a non-EOA address. Using whitelisted a[0] as workaround
# instead of sending the transaction from Vault/KeyManager/StakeManager
def test_consumeKeyNonce_check_whitelisted(a, cfAW):
    for addr in cfAW.whitelisted:
        sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cfAW.keyManager.address)
        # cfAW.ALICE.transfer(to=addr, amount=ONE_ETH)
        # Sending transaction from whitelisted non-EOA address as a workaround
        cfAW.keyManager.consumeKeyNonce(
            # sigData, cleanHexStr(sigData[2]), {"from": addr}
            sigData,
            cleanHexStr(sigData[2]),
            {"from": a[0]},
        )


def test_consumeKeyNonce_check_nonwhitelisted(a, cf):
    # Current whitelisted [cf.vault, cf.keyManager, cf.stakeManager, cf.flip]
    for addr in list(a):
        sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
        with reverts(REV_MSG_WHITELIST):
            cf.keyManager.consumeKeyNonce(sigData, cleanHexStr(sigData[2]))


def test_consumeKeyNonce_rev_used_nonce(a, cfAW):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cfAW.keyManager.address)
    cfAW.keyManager.consumeKeyNonce(
        sigData,
        cleanHexStr(sigData[2]),
    )

    # Replay attack
    with reverts(REV_MSG_KEYMANAGER_NONCE):
        cfAW.keyManager.consumeKeyNonce(
            sigData,
            cleanHexStr(sigData[2]),
        )
