from consts import *
from shared_tests import *
from brownie import reverts, chain
from brownie.test import given, strategy


def test_setAggKeyWithAggKey_setAggKeyWithAggKey(cf):
    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    # Try to set agg key with old agg key (we're not "changing" the agg key here but it should fail nonetheless since the contract does not
    # ever check that they are different)
    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), AGG_SIGNER_1.getPubData()
    )
    with reverts(REV_MSG_SIG):
        cf.keyManager.setAggKeyWithAggKey(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            AGG_SIGNER_1.getPubData(),
        )

    # Change agg key back to signer one
    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), AGG_SIGNER_1.getPubData()
    )
    tx = cf.keyManager.setAggKeyWithAggKey(
        AGG_SIGNER_2.getSigData(callDataNoSig, cf.keyManager.address),
        AGG_SIGNER_1.getPubData(),
    )

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert tx.events["AggKeySetByAggKey"][0].values() == [
        AGG_SIGNER_2.getPubDataWith0x(),
        AGG_SIGNER_1.getPubDataWith0x(),
    ]
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR


def test_setGovKeyWithGovKey_setAggKeyWithGovKey(cf):
    # Changing the agg key with the gov key should fail if the delay hasn't been long enough yet
    # No time has passed since the constructor has set the first value of _lastValidateTime
    with reverts(REV_MSG_DELAY):
        cf.keyManager.setAggKeyWithGovKey(
            AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR_2}
        )

    chain.sleep(AGG_KEY_TIMEOUT)

    # Change the gov key
    setGovKeyWithGovKey_test(cf)

    # Trying to change agg key with old gov key should revert
    with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
        cf.keyManager.setAggKeyWithGovKey(
            AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR}
        )

    # Change agg key with gov key - should not revert - setGovKeyWithGovKey doesn't update _lastValidateTime
    tx = cf.keyManager.setAggKeyWithGovKey(
        AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR_2}
    )

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert tx.events["AggKeySetByGovKey"][0].values() == [
        AGG_SIGNER_1.getPubDataWith0x(),
        AGG_SIGNER_2.getPubDataWith0x(),
    ]
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR_2


# Check that _withAggKey calls update the _lastValidateTime
def test_setAggKeyWithGovKey_setKeyWithAggKey(cf):
    # Changing the agg key with the gov key should fail if the delay hasn't been long enough yet
    # No time has passed since the constructor has set the first value of _lastValidateTime
    with reverts(REV_MSG_DELAY):
        cf.keyManager.setAggKeyWithGovKey(
            AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR}
        )

    chain.sleep(AGG_KEY_TIMEOUT)

    setAggKeyWithAggKey_test(cf)

    # Reverts due to setAggKeyWithAggKey updating the _lastValidateTime
    with reverts(REV_MSG_DELAY):
        cf.keyManager.setAggKeyWithGovKey(
            AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR}
        )

    chain.sleep(AGG_KEY_TIMEOUT)

    # Change agg key with gov key
    cf.keyManager.setAggKeyWithGovKey(AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR})

    # setGovKeyWithAggKey
    callDataNoSig = cf.keyManager.setGovKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), cf.GOVERNOR
    )
    cf.keyManager.setGovKeyWithAggKey(
        AGG_SIGNER_2.getSigData(callDataNoSig, cf.keyManager.address),
        cf.GOVERNOR,
    )
    with reverts(REV_MSG_DELAY):
        cf.keyManager.setAggKeyWithGovKey(
            AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR}
        )

    chain.sleep(AGG_KEY_TIMEOUT)

    cf.keyManager.setAggKeyWithGovKey(AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR})

    # setCommKeyWithAggKey
    callDataNoSig = cf.keyManager.setCommKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), cf.communityKey
    )
    cf.keyManager.setCommKeyWithAggKey(
        AGG_SIGNER_2.getSigData(callDataNoSig, cf.keyManager.address),
        cf.communityKey,
    )

    with reverts(REV_MSG_DELAY):
        cf.keyManager.setAggKeyWithGovKey(
            AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR}
        )

    chain.sleep(AGG_KEY_TIMEOUT)

    cf.keyManager.setAggKeyWithGovKey(AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR})


# Check that no AggKey call can be made with an old aggKey
@given(st_sender=strategy("address"))
def test_setAggKeyWithAggKey_setKeyWithAggKey_rev(cf, st_sender):
    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    # setAggKeyWithAggKey
    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), AGG_SIGNER_1.getPubData()
    )
    with reverts(REV_MSG_SIG):
        cf.keyManager.setAggKeyWithAggKey(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            AGG_SIGNER_1.getPubData(),
        )

    # setGovKeyWithAggKey
    callDataNoSig = cf.keyManager.setGovKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), st_sender
    )
    with reverts(REV_MSG_SIG):
        cf.keyManager.setGovKeyWithAggKey(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            st_sender,
        )

    # setCommKeyWithAggKey
    callDataNoSig = cf.keyManager.setGovKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), st_sender
    )
    with reverts(REV_MSG_SIG):
        cf.keyManager.setGovKeyWithAggKey(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            st_sender,
        )
