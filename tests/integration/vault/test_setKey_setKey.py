from consts import *
from shared_tests import *
from brownie import reverts


def test_setAggKeyByAggKey_setAggKeyByAggKey(vault):
    # Change agg keys
    testSetAggKeyByAggKey(vault)

    # Try to change agg key with old agg key
    callDataNoSig = vault.setAggKeyByAggKey.encode_input(0, 0, *GOV_SIGNER_1.getPubData())
    with reverts(REV_MSG_SIG):
        vault.setAggKeyByAggKey(*AGG_SIGNER_1.getSigData(callDataNoSig), *GOV_SIGNER_1.getPubData())

    # Try to change agg key with gov key
    with reverts(REV_MSG_SIG):
        vault.setAggKeyByAggKey(*GOV_SIGNER_1.getSigData(callDataNoSig), *GOV_SIGNER_1.getPubData())
    
    # Change agg key to gov key since there's no AGG_SIGNER_3
    tx = vault.setAggKeyByAggKey(*AGG_SIGNER_2.getSigData(callDataNoSig), *GOV_SIGNER_1.getPubData())

    assert vault.getAggregateKeyData() == GOV_SIGNER_1.getPubDataWith0x()
    assert tx.events["KeyChange"][0].values() == [True, *AGG_SIGNER_2.getPubDataWith0x(), *GOV_SIGNER_1.getPubDataWith0x()]
    assert vault.getGovernanceKeyData() == GOV_SIGNER_1.getPubDataWith0x()
    txTimeTest(vault.getLastValidateTime(), tx)


def test_setGovKeyByGovKey_setAggKeyByGovKey(vault):
    # Change the gov key
    testSetGovKeyByGovKey(vault)

    # Try to change agg key with old gov key
    callDataNoSig = vault.setAggKeyByGovKey.encode_input(0, 0, *AGG_SIGNER_2.getPubData())
    with reverts(REV_MSG_SIG):
        vault.setAggKeyByGovKey(*GOV_SIGNER_1.getSigData(callDataNoSig), *AGG_SIGNER_2.getPubData())
    
    # Change agg key with gov key
    tx = vault.setAggKeyByGovKey(*GOV_SIGNER_2.getSigData(callDataNoSig), *AGG_SIGNER_2.getPubData())

    assert vault.getAggregateKeyData() == AGG_SIGNER_2.getPubDataWith0x()
    assert tx.events["KeyChange"][0].values() == [True, *AGG_SIGNER_1.getPubDataWith0x(), *AGG_SIGNER_2.getPubDataWith0x()]
    assert vault.getGovernanceKeyData() == GOV_SIGNER_2.getPubDataWith0x()
    txTimeTest(vault.getLastValidateTime(), tx)


