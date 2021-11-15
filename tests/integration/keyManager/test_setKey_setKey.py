from consts import *
from shared_tests import *
from brownie import reverts, chain


def test_setAggKeyWithAggKey_setAggKeyWithAggKey(cfAW):
    # Change agg keys
    setAggKeyWithAggKey_test(cfAW)

    # Try to change agg key with old agg key
    callDataNoSig = cfAW.keyManager.setAggKeyWithAggKey.encode_input(agg_null_sig(cfAW.keyManager.address, chain.id), GOV_SIGNER_1.getPubData())
    with reverts(REV_MSG_SIG):
        cfAW.keyManager.setAggKeyWithAggKey(AGG_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address), GOV_SIGNER_1.getPubData())

    # Try to change agg key with gov key
    callDataNoSig = cfAW.keyManager.setAggKeyWithAggKey.encode_input(gov_null_sig(cfAW.keyManager.address, chain.id), GOV_SIGNER_1.getPubData())
    with reverts(REV_MSG_SIG):
        cfAW.keyManager.setAggKeyWithAggKey(GOV_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address), GOV_SIGNER_1.getPubData())

    # Change agg key to gov key since there's no AGG_SIGNER_3
    callDataNoSig = cfAW.keyManager.setAggKeyWithAggKey.encode_input(agg_null_sig(cfAW.keyManager.address, chain.id), GOV_SIGNER_1.getPubData())
    tx = cfAW.keyManager.setAggKeyWithAggKey(AGG_SIGNER_2.getSigData(callDataNoSig, cfAW.keyManager.address), GOV_SIGNER_1.getPubData())

    assert cfAW.keyManager.getAggregateKey() == GOV_SIGNER_1.getPubDataWith0x()
    assert tx.events["AggKeySetByAggKey"][0].values() == [AGG_SIGNER_2.getPubDataWith0x(), GOV_SIGNER_1.getPubDataWith0x()]
    assert cfAW.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()
    # txTimeTest(cfAW.keyManager.getLastValidateTime(), tx)


def test_setGovKeyWithGovKey_setAggKeyWithGovKey(cfAW):
    # Change the gov key
    setGovKeyWithGovKey_test(cfAW)

    callDataNoSig = cfAW.keyManager.setAggKeyWithGovKey.encode_input(gov_null_sig(cfAW.keyManager.address, chain.id), AGG_SIGNER_2.getPubData())
    # Changing the agg key with the gov key should fail if the delay hasn't been long enough yet
    with reverts(REV_MSG_DELAY):
        cfAW.keyManager.setAggKeyWithGovKey(GOV_SIGNER_2.getSigData(callDataNoSig, cfAW.keyManager.address), AGG_SIGNER_2.getPubData())

    chain.sleep(AGG_KEY_TIMEOUT)
    # Trying to change agg key with old gov key should revert
    callDataNoSig = cfAW.keyManager.setAggKeyWithGovKey.encode_input(gov_null_sig(cfAW.keyManager.address, chain.id), AGG_SIGNER_2.getPubData())
    with reverts(REV_MSG_SIG):
        cfAW.keyManager.setAggKeyWithGovKey(GOV_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address), AGG_SIGNER_2.getPubData())

    # Change agg key with gov key
    callDataNoSig = cfAW.keyManager.setAggKeyWithGovKey.encode_input(gov_null_sig(cfAW.keyManager.address, chain.id), AGG_SIGNER_2.getPubData())
    tx = cfAW.keyManager.setAggKeyWithGovKey(GOV_SIGNER_2.getSigData(callDataNoSig, cfAW.keyManager.address), AGG_SIGNER_2.getPubData())

    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert tx.events["AggKeySetByGovKey"][0].values() == [AGG_SIGNER_1.getPubDataWith0x(), AGG_SIGNER_2.getPubDataWith0x()]
    assert cfAW.keyManager.getGovernanceKey() == GOV_SIGNER_2.getPubDataWith0x()
    # txTimeTest(cfAW.keyManager.getLastValidateTime(), tx)
