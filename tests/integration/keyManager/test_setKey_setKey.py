from consts import *
from shared_tests import *
from brownie import reverts, chain
from brownie.test import given, strategy


def test_setAggKeyWithAggKey_setAggKeyWithAggKey(cf):
    # Change agg keys
    setAggKeyWithAggKey_test(cf)

    # Try to set agg key with old agg key (we're not "changing" the agg key here but it should fail nonetheless since the contract does not
    # ever check that they are different)
    with reverts(REV_MSG_SIG):
        signed_call_cf(cf, cf.keyManager.setAggKeyWithAggKey, AGG_SIGNER_1.getPubData())

    # Change agg key back to signer one
    tx = signed_call_cf(
        cf,
        cf.keyManager.setAggKeyWithAggKey,
        AGG_SIGNER_1.getPubData(),
        signer=AGG_SIGNER_2,
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
    signed_call_cf(
        cf, cf.keyManager.setGovKeyWithAggKey, cf.GOVERNOR, signer=AGG_SIGNER_2
    )

    with reverts(REV_MSG_DELAY):
        cf.keyManager.setAggKeyWithGovKey(
            AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR}
        )

    chain.sleep(AGG_KEY_TIMEOUT)

    cf.keyManager.setAggKeyWithGovKey(AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR})

    # setCommKeyWithAggKey
    signed_call_cf(
        cf, cf.keyManager.setCommKeyWithAggKey, cf.communityKey, signer=AGG_SIGNER_2
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
    with reverts(REV_MSG_SIG):
        signed_call_cf(cf, cf.keyManager.setAggKeyWithAggKey, AGG_SIGNER_1.getPubData())

    # setGovKeyWithAggKey
    with reverts(REV_MSG_SIG):
        signed_call_cf(cf, cf.keyManager.setGovKeyWithAggKey, st_sender)

    # setCommKeyWithAggKey
    with reverts(REV_MSG_SIG):
        signed_call_cf(cf, cf.keyManager.setGovKeyWithAggKey, st_sender)
