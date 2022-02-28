from consts import *
from shared_tests import *
from brownie import reverts, chain


def test_isValidSig_setAggKeyWithAggKey_validate(cfAW):
    # txTimeTest(cfAW.keyManager.getLastValidateTime(), cfAW.keyManager.tx)

    # Should validate with current keys and revert with future keys
    isValidSig_test(cfAW, AGG_SIGNER_1)
    isValidSig_rev_test(cfAW, AGG_SIGNER_2)

    # Should change key successfully
    setAggKeyWithAggKey_test(cfAW)

    # Should validate with current keys and revert with past keys
    isValidSig_rev_test(cfAW, AGG_SIGNER_1)
    isValidSig_test(cfAW, AGG_SIGNER_2)


def test_isValid_setGovKeyWithGovKey_isValid_setAggKeyWithGovKey_isValidSig(cfAW):
    # txTimeTest(cfAW.keyManager.getLastValidateTime(), cfAW.keyManager.tx)

    # Should validate with current keys and revert with future keys
    isValidSig_test(cfAW, AGG_SIGNER_1)
    isValidSig_rev_test(cfAW, AGG_SIGNER_2)

    # Should change key successfully
    setGovKeyWithGovKey_test(cfAW)

    # Should validate with current keys and revert with past and future keys
    isValidSig_test(cfAW, AGG_SIGNER_1)
    isValidSig_rev_test(cfAW, AGG_SIGNER_2)

    # Should change key successfully
    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cfAW.keyManager.getGovernanceKey() == cfAW.GOVERNOR_2

    # Changing the agg key with the gov key should fail if the delay hasn't been long enough yet
    with reverts(REV_MSG_DELAY):
        cfAW.keyManager.setAggKeyWithGovKey(AGG_SIGNER_2.getPubData(), {"from": cfAW.GOVERNOR_2})
    chain.sleep(AGG_KEY_TIMEOUT)
    tx = cfAW.keyManager.setAggKeyWithGovKey(AGG_SIGNER_2.getPubData(), {"from": cfAW.GOVERNOR_2})

    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert cfAW.keyManager.getGovernanceKey() == cfAW.GOVERNOR_2
    # txTimeTest(cfAW.keyManager.getLastValidateTime(), tx)
    assert tx.events["AggKeySetByGovKey"][0].values() == [AGG_SIGNER_1.getPubDataWith0x(), AGG_SIGNER_2.getPubDataWith0x()]

    # Should validate with current keys and revert with past keys
    isValidSig_rev_test(cfAW, AGG_SIGNER_1)
    isValidSig_test(cfAW, AGG_SIGNER_2)
