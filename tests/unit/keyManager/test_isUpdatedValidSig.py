from pprint import pprint
from consts import *
from brownie import reverts, chain
from shared_tests import *
from brownie.test import given, strategy


def test_isUpdatedValidSig(cfAW):
    nonce = nonces[AGG]
    assert not cfAW.keyManager.isNonceUsedByAggKey(nonce)

    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cfAW.keyManager.address)
    tx = cfAW.keyManager.isUpdatedValidSig(sigData, cleanHexStr(sigData[2]))

    assert nonce == sigData[4]
    assert tx.return_value == True
    assert cfAW.keyManager.isNonceUsedByAggKey(sigData[4])


def test_isUpdatedValidSig_rev_msgHash(cfAW):
    # Fails because msgHash in sigData is a hash of JUNK_HEX_PAD, whereas JUNK_HEX_PAD
    # is used directly for contractMsgHash
    with reverts(REV_MSG_MSGHASH):
        cfAW.keyManager.isUpdatedValidSig(
            AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cfAW.keyManager.address), JUNK_HEX_PAD
        )


def test_isUpdatedValidSig_rev_sig(cfAW):
    sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cfAW.keyManager.address)
    sigData[3] = JUNK_HEX
    with reverts(REV_MSG_SIG):
        cfAW.keyManager.isUpdatedValidSig(sigData, cleanHexStr(sigData[2]))


@given(addr=strategy("address"))
def test_isUpdatedValidSig_rev_keyManAddr(a, cfAW, addr):
    if addr != cfAW.keyManager:
        sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, addr)
        with reverts(REV_MSG_WRONG_KEYMANADDR):
            cfAW.keyManager.isUpdatedValidSig(sigData, cleanHexStr(sigData[2]))


@given(chainID=strategy("uint256"))
def test_isUpdatedValidSig_rev_chainID(a, cfAW, chainID):
    if chainID != chain.id:
        sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cfAW.keyManager.address)
        sigData[1] = chainID
        with reverts(REV_MSG_WRONG_CHAINID):
            cfAW.keyManager.isUpdatedValidSig(sigData, cleanHexStr(sigData[2]))


def test_isUpdatedValidSig_check_all(a, cf):
    whitelisted = [cf.vault, cf.keyManager, cf.stakeManager]
    for addr in whitelisted + list(a):
        if addr in whitelisted:
            sigData = AGG_SIGNER_1.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
            cf.ALICE.transfer(to=addr, amount=ONE_ETH)
            cf.keyManager.isUpdatedValidSig(
                sigData, cleanHexStr(sigData[2]), {"from": addr}
            )
        else:
            with reverts(REV_MSG_WHITELIST):
                cf.keyManager.isUpdatedValidSig(sigData, cleanHexStr(sigData[2]))
