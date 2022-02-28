from consts import *
from shared_tests import *
from brownie import reverts, chain


def test_setAggKeyWithAggKey_setAggKeyWithAggKey(cfAW):
    # Change agg keys
    setAggKeyWithAggKey_test(cfAW)

    # Try to set agg key with old agg key (we're not "changing" the agg key here but it should fail nonetheless since the contract does not
    # ever check that they are different)
    callDataNoSig = cfAW.keyManager.setAggKeyWithAggKey.encode_input(agg_null_sig(cfAW.keyManager.address, chain.id), AGG_SIGNER_1.getPubData())
    with reverts(REV_MSG_SIG):
        cfAW.keyManager.setAggKeyWithAggKey(AGG_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address), AGG_SIGNER_1.getPubData())

    # Change agg key back to signer one
    callDataNoSig = cfAW.keyManager.setAggKeyWithAggKey.encode_input(agg_null_sig(cfAW.keyManager.address, chain.id), AGG_SIGNER_1.getPubData())
    tx = cfAW.keyManager.setAggKeyWithAggKey(AGG_SIGNER_2.getSigData(callDataNoSig, cfAW.keyManager.address), AGG_SIGNER_1.getPubData())

    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert tx.events["AggKeySetByAggKey"][0].values() == [AGG_SIGNER_2.getPubDataWith0x(), AGG_SIGNER_1.getPubDataWith0x()]
    assert cfAW.keyManager.getGovernanceKey() == cfAW.GOVERNOR
    # txTimeTest(cfAW.keyManager.getLastValidateTime(), tx)


def test_setGovKeyWithGovKey_setAggKeyWithGovKey(cfAW):
    # Change the gov key
    setGovKeyWithGovKey_test(cfAW)

    # Changing the agg key with the gov key should fail if the delay hasn't been long enough yet
    with reverts(REV_MSG_DELAY):
        cfAW.keyManager.setAggKeyWithGovKey(AGG_SIGNER_2.getPubData(), {"from": cfAW.GOVERNOR_2})

    chain.sleep(AGG_KEY_TIMEOUT)
    # Trying to change agg key with old gov key should revert
    with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
        cfAW.keyManager.setAggKeyWithGovKey(AGG_SIGNER_2.getPubData(), {"from": cfAW.GOVERNOR})

    # Change agg key with gov key
    tx = cfAW.keyManager.setAggKeyWithGovKey(AGG_SIGNER_2.getPubData(), {"from": cfAW.GOVERNOR_2})

    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert tx.events["AggKeySetByGovKey"][0].values() == [AGG_SIGNER_1.getPubDataWith0x(), AGG_SIGNER_2.getPubDataWith0x()]
    assert cfAW.keyManager.getGovernanceKey() == cfAW.GOVERNOR_2
    # txTimeTest(cfAW.keyManager.getLastValidateTime(), tx)
