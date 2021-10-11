from consts import *
from shared_tests import *
from brownie import reverts, chain


def test_isValidSig_setAggKeyWithAggKey_validate(cfAW):
    txTimeTest(cfAW.keyManager.getLastValidateTime(), cfAW.keyManager.tx)

    # Should validate with current keys and revert with future keys
    isValidSig_test(cfAW, AGG_SIGNER_1)
    isValidSig_rev_test(cfAW, AGG_SIGNER_2)
    isValidSig_test(cfAW, GOV_SIGNER_1)

    # Should change key successfully
    setAggKeyWithAggKey_test(cfAW)

    # Should validate with current keys and revert with past keys
    isValidSig_rev_test(cfAW, AGG_SIGNER_1)
    isValidSig_test(cfAW, AGG_SIGNER_2)
    isValidSig_test(cfAW, GOV_SIGNER_1)


def test_isValid_setGovKeyWithGovKey_isValid_setAggKeyWithGovKey_isValidSig(cfAW):
    txTimeTest(cfAW.keyManager.getLastValidateTime(), cfAW.keyManager.tx)

    # Should validate with current keys and revert with future keys
    isValidSig_test(cfAW, AGG_SIGNER_1)
    isValidSig_rev_test(cfAW, AGG_SIGNER_2)
    isValidSig_test(cfAW, GOV_SIGNER_1)
    isValidSig_rev_test(cfAW, GOV_SIGNER_2)

    # Should change key successfully
    setGovKeyWithGovKey_test(cfAW)

    # Should validate with current keys and revert with past and future keys
    isValidSig_test(cfAW, AGG_SIGNER_1)
    isValidSig_rev_test(cfAW, AGG_SIGNER_2)
    isValidSig_rev_test(cfAW, GOV_SIGNER_1)
    isValidSig_test(cfAW, GOV_SIGNER_2)

    # Should change key successfully
    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cfAW.keyManager.getGovernanceKey() == GOV_SIGNER_2.getPubDataWith0x()

    # Changing the agg key with the gov key should fail if the delay hasn't been long enough yet
    callDataNoSig = cfAW.keyManager.setAggKeyWithGovKey.encode_input(gov_null_sig(), AGG_SIGNER_2.getPubData())
    with reverts(REV_MSG_DELAY):
        cfAW.keyManager.setAggKeyWithGovKey(GOV_SIGNER_2.getSigData(callDataNoSig), AGG_SIGNER_2.getPubData())
    
    chain.sleep(AGG_KEY_TIMEOUT)
    callDataNoSig = cfAW.keyManager.setAggKeyWithGovKey.encode_input(gov_null_sig(), AGG_SIGNER_2.getPubData())
    tx = cfAW.keyManager.setAggKeyWithGovKey(GOV_SIGNER_2.getSigData(callDataNoSig), AGG_SIGNER_2.getPubData())

    assert cfAW.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert cfAW.keyManager.getGovernanceKey() == GOV_SIGNER_2.getPubDataWith0x()
    txTimeTest(cfAW.keyManager.getLastValidateTime(), tx)
    assert tx.events["KeyChange"][0].values() == [False, AGG_SIGNER_1.getPubDataWith0x(), AGG_SIGNER_2.getPubDataWith0x()]

    # Should validate with current keys and revert with past keys
    isValidSig_rev_test(cfAW, AGG_SIGNER_1)
    isValidSig_test(cfAW, AGG_SIGNER_2)
    isValidSig_rev_test(cfAW, GOV_SIGNER_1)
    isValidSig_test(cfAW, GOV_SIGNER_2)
