from consts import *
from shared_tests import *
from brownie import reverts, chain


def test_canConsumeKeyNonce_setAggKeyWithAggKey_validate(cfAW):
    # Should validate with current keys and revert with future keys
    canConsumeKeyNonce_test(cfAW, AGG_SIGNER_1)
    canConsumeKeyNonce_rev_test(cfAW, AGG_SIGNER_2)

    # Should change key successfully
    setAggKeyWithAggKey_test(cfAW)

    # Should validate with current keys and revert with past keys
    canConsumeKeyNonce_rev_test(cfAW, AGG_SIGNER_1)
    canConsumeKeyNonce_test(cfAW, AGG_SIGNER_2)


def test_isValid_setGovKeyWithGovKey_isValid_setAggKeyWithGovKey_canConsumeKeyNonce(
    cfAW,
):
    # Should validate with current keys and revert with future keys
    canConsumeKeyNonce_test(cfAW, AGG_SIGNER_1)
    canConsumeKeyNonce_rev_test(cfAW, AGG_SIGNER_2)

    # Should change key successfully
    setGovKeyWithGovKey_test(cfAW)

    # Should validate with current keys and revert with past and future keys
    canConsumeKeyNonce_test(cfAW, AGG_SIGNER_1)
    canConsumeKeyNonce_rev_test(cfAW, AGG_SIGNER_2)

    # Should change key successfully
    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cfAW.keyManager.getGovernanceKey() == cfAW.GOVERNOR_2

    # Changing the agg key with the gov key should fail if the delay hasn't been long enough yet
    with reverts(REV_MSG_DELAY):
        cfAW.keyManager.setAggKeyWithGovKey(
            AGG_SIGNER_2.getPubData(), {"from": cfAW.GOVERNOR_2}
        )
    chain.sleep(AGG_KEY_TIMEOUT)
    tx = cfAW.keyManager.setAggKeyWithGovKey(
        AGG_SIGNER_2.getPubData(), {"from": cfAW.GOVERNOR_2}
    )

    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert cfAW.keyManager.getGovernanceKey() == cfAW.GOVERNOR_2

    assert tx.events["AggKeySetByGovKey"][0].values() == [
        AGG_SIGNER_1.getPubDataWith0x(),
        AGG_SIGNER_2.getPubDataWith0x(),
    ]

    # Should validate with current keys and revert with past keys
    canConsumeKeyNonce_rev_test(cfAW, AGG_SIGNER_1)
    canConsumeKeyNonce_test(cfAW, AGG_SIGNER_2)
