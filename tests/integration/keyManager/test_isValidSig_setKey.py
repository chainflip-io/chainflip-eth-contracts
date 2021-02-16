from consts import *
from shared_tests import *
from brownie import reverts, chain


def test_isValidSig_setAggKeyWithAggKey_validate(cf):
    txTimeTest(cf.keyManager.getLastValidateTime(), cf.keyManager.tx)

    # Should validate with current keys and revert with future keys
    isValidSig_test(cf, AGG_SIGNER_1)
    isValidSig_rev_test(cf, AGG_SIGNER_2)
    isValidSig_test(cf, GOV_SIGNER_1)

    # Should change key successfully
    setAggKeyWithAggKey_test(cf)

    # Should validate with current keys and revert with past keys
    isValidSig_rev_test(cf, AGG_SIGNER_1)
    isValidSig_test(cf, AGG_SIGNER_2)
    isValidSig_test(cf, GOV_SIGNER_1)


def test_isValid_setGovKeyWithGovKey_isValid_setAggKeyWithGovKey_isValidSig(cf):
    txTimeTest(cf.keyManager.getLastValidateTime(), cf.keyManager.tx)

    # Should validate with current keys and revert with future keys
    isValidSig_test(cf, AGG_SIGNER_1)
    isValidSig_rev_test(cf, AGG_SIGNER_2)
    isValidSig_test(cf, GOV_SIGNER_1)
    isValidSig_rev_test(cf, GOV_SIGNER_2)

    # Should change key successfully
    setGovKeyWithGovKey_test(cf)

    # Should validate with current keys and revert with past and future keys
    isValidSig_test(cf, AGG_SIGNER_1)
    isValidSig_rev_test(cf, AGG_SIGNER_2)
    isValidSig_rev_test(cf, GOV_SIGNER_1)
    isValidSig_test(cf, GOV_SIGNER_2)

    # Should change key successfully
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_2.getPubDataWith0x()

    callDataNoSig = cf.keyManager.setAggKeyWithGovKey.encode_input(NULL_SIG_DATA, AGG_SIGNER_2.getPubData())
    # Changing the agg key with the gov key should fail if the delay hasn't been long enough yet
    with reverts(REV_MSG_DELAY):
        cf.keyManager.setAggKeyWithGovKey(GOV_SIGNER_2.getSigData(callDataNoSig), AGG_SIGNER_2.getPubData())
    
    chain.sleep(AGG_KEY_TIMEOUT)
    tx = cf.keyManager.setAggKeyWithGovKey(GOV_SIGNER_2.getSigData(callDataNoSig), AGG_SIGNER_2.getPubData())

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_2.getPubDataWith0x()
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)
    assert tx.events["KeyChange"][0].values() == [False, AGG_SIGNER_1.getPubDataWith0x(), AGG_SIGNER_2.getPubDataWith0x()]

    # Should validate with current keys and revert with past keys
    isValidSig_rev_test(cf, AGG_SIGNER_1)
    isValidSig_test(cf, AGG_SIGNER_2)
    isValidSig_rev_test(cf, GOV_SIGNER_1)
    isValidSig_test(cf, GOV_SIGNER_2)
