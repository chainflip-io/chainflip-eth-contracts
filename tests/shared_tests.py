from consts import *
from brownie import reverts


# Test with timestamp-1 because of an error where there's a difference of 1s
# because the evm and local clock were out of sync or something... not 100% sure why,
# but some tests occasionally fail for this reason even though they succeed most
# of the time with no changes to the contract or test code
def txTimeTest(time, tx):
    assert time >= tx.timestamp and time <= (tx.timestamp+2)



# ----------Vault---------- 

# Set keys


def setAggKeyWithAggKey_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()

    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(NULL_SIG_DATA, AGG_SIGNER_2.getPubData())
    tx = cf.keyManager.setAggKeyWithAggKey(AGG_SIGNER_1.getSigData(callDataNoSig), AGG_SIGNER_2.getPubData())

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)
    assert tx.events["KeyChange"][0].values() == [True, AGG_SIGNER_1.getPubDataWith0x(), AGG_SIGNER_2.getPubDataWith0x()]


def setAggKeyWithGovKey_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()

    callDataNoSig = cf.keyManager.setAggKeyWithGovKey.encode_input(NULL_SIG_DATA, AGG_SIGNER_2.getPubData())
    tx = cf.keyManager.setAggKeyWithGovKey(GOV_SIGNER_1.getSigData(callDataNoSig), AGG_SIGNER_2.getPubData())

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_2.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)
    assert tx.events["KeyChange"][0].values() == [False, AGG_SIGNER_1.getPubDataWith0x(), AGG_SIGNER_2.getPubDataWith0x()]


def setGovKeyWithGovKey_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_1.getPubDataWith0x()

    callDataNoSig = cf.keyManager.setGovKeyWithGovKey.encode_input(NULL_SIG_DATA, GOV_SIGNER_2.getPubData())
    tx = cf.keyManager.setGovKeyWithGovKey(GOV_SIGNER_1.getSigData(callDataNoSig), GOV_SIGNER_2.getPubData())

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == GOV_SIGNER_2.getPubDataWith0x()
    txTimeTest(cf.keyManager.getLastValidateTime(), tx)
    assert tx.events["KeyChange"][0].values() == [False, GOV_SIGNER_1.getPubDataWith0x(), GOV_SIGNER_2.getPubDataWith0x()]


def setKey_rev_pubKeyX_test(cf, fcn, signer):
    newKey = AGG_SIGNER_2.getPubData()
    newKey[0] = 0
    callDataNoSig = fcn.encode_input(NULL_SIG_DATA, newKey)
    with reverts(REV_MSG_PUBKEYX):
        fcn(signer.getSigData(callDataNoSig), newKey)


def setKey_rev_nonceTimesGAddr_test(cf, fcn, signer):
    newKey = AGG_SIGNER_2.getPubData()
    newKey[2] = ZERO_ADDR
    callDataNoSig = fcn.encode_input(NULL_SIG_DATA, newKey)
    with reverts(REV_MSG_NONCETIMESGADDR):
        fcn(signer.getSigData(callDataNoSig), newKey)


def setKey_rev_msgHash_test(cf, fcn, signer):
    callDataNoSig = fcn.encode_input(NULL_SIG_DATA, AGG_SIGNER_2.getPubData())
    sigData = signer.getSigData(callDataNoSig)
    sigData[0] += 1
    with reverts(REV_MSG_MSGHASH):
        fcn(sigData, AGG_SIGNER_2.getPubData())


def setKey_rev_sig_test(cf, fcn, signer):
    callDataNoSig = fcn.encode_input(NULL_SIG_DATA, AGG_SIGNER_2.getPubData())
    sigData = signer.getSigData(callDataNoSig)
    sigData[1] += 1
    with reverts(REV_MSG_SIG):
        fcn(sigData, AGG_SIGNER_2.getPubData())
