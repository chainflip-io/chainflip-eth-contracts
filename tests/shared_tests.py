from consts import *
from brownie import reverts



# ----------Vault---------- 

# Set keys

def testSetAggKeyByAggKey(vault):
    assert vault.getAggregateKeyData() == AGG_SIGNER_1.getPubDataWith0x()
    assert vault.getGovernanceKeyData() == GOV_SIGNER_1.getPubDataWith0x()

    callDataNoSig = vault.setAggKeyByAggKey.encode_input(0, 0, *AGG_SIGNER_2.getPubData())
    tx = vault.setAggKeyByAggKey(*AGG_SIGNER_1.getSigData(callDataNoSig), *AGG_SIGNER_2.getPubData())

    assert vault.getAggregateKeyData() == AGG_SIGNER_2.getPubDataWith0x()
    assert tx.events["KeyChange"][0].values() == [True, *AGG_SIGNER_1.getPubDataWith0x(), *AGG_SIGNER_2.getPubDataWith0x()]
    assert vault.getGovernanceKeyData() == GOV_SIGNER_1.getPubDataWith0x()


def testSetAggKeyByGovKey(vault):
    assert vault.getAggregateKeyData() == AGG_SIGNER_1.getPubDataWith0x()
    assert vault.getGovernanceKeyData() == GOV_SIGNER_1.getPubDataWith0x()

    callDataNoSig = vault.setAggKeyByGovKey.encode_input(0, 0, *AGG_SIGNER_2.getPubData())
    tx = vault.setAggKeyByGovKey(*GOV_SIGNER_1.getSigData(callDataNoSig), *AGG_SIGNER_2.getPubData())

    assert vault.getAggregateKeyData() == AGG_SIGNER_2.getPubDataWith0x()
    assert tx.events["KeyChange"][0].values() == [True, *AGG_SIGNER_1.getPubDataWith0x(), *AGG_SIGNER_2.getPubDataWith0x()]
    assert vault.getGovernanceKeyData() == GOV_SIGNER_1.getPubDataWith0x()


def testSetGovKeyByGovKey(vault):
    assert vault.getAggregateKeyData() == AGG_SIGNER_1.getPubDataWith0x()
    assert vault.getGovernanceKeyData() == GOV_SIGNER_1.getPubDataWith0x()

    callDataNoSig = vault.setGovKeyByGovKey.encode_input(0, 0, *GOV_SIGNER_2.getPubData())
    tx = vault.setGovKeyByGovKey(*GOV_SIGNER_1.getSigData(callDataNoSig), *GOV_SIGNER_2.getPubData())

    assert vault.getAggregateKeyData() == AGG_SIGNER_1.getPubDataWith0x()
    assert vault.getGovernanceKeyData() == GOV_SIGNER_2.getPubDataWith0x()
    assert tx.events["KeyChange"][0].values() == [False, *GOV_SIGNER_1.getPubDataWith0x(), *GOV_SIGNER_2.getPubDataWith0x()]



# Test with timestamp-1 because of an error where there's a difference of 1s
# because the evm and local clock were out of sync or something... not 100% sure why,
# but some tests occasionally fail for this reason even though they succeed most
# of the time with no changes to the contract or test code
def txTimeTest(time, tx):
    assert time >= tx.timestamp or time <= (tx.timestamp+2)
