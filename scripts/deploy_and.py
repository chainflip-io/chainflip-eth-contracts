import sys
from os import path
sys.path.append(path.abspath('tests'))
from consts import *
from brownie import chain, accounts, KeyManager, Vault, StakeManager, FLIP, chain, network
from deploy import deploy_initial_ChainFlip_contracts

print(network.show_active())

DEPLOYER = accounts[0]
ALICE = accounts[1]
BOB = accounts[2]
CHARLIE = accounts[3]
DENICE = accounts[4]

cf = deploy_initial_ChainFlip_contracts(DEPLOYER, KeyManager, Vault, StakeManager, FLIP)

cf.flip.transfer(ALICE, MAX_TEST_STAKE, {'from': DEPLOYER})
cf.flip.approve(cf.stakeManager, MAX_TEST_STAKE, {'from': ALICE})
cf.flip.transfer(BOB, MAX_TEST_STAKE, {'from': DEPLOYER})
cf.flip.approve(cf.stakeManager, MAX_TEST_STAKE, {'from': BOB})

print("========================= 😎  Deployed! 😎 ==========================\n")
print(f"KeyManager deployed by {DEPLOYER} to address: {cf.keyManager.address}\n")
print(f"Vault deployed by {DEPLOYER} to address: {cf.vault.address}\n")
print(f"StakeManager deployed by {DEPLOYER} to address: {cf.stakeManager.address}\n")
print(f"FLIP deployed by {DEPLOYER} to address: {cf.flip.address}\n")
print("======================================================================")

def main():
    print()

def all_events():
    all_stakeManager_events()
    all_keyManager_events()

def all_stakeManager_events():
    print(f"\n💰 Alice stakes {MIN_STAKE} with nodeID {JUNK_INT}\n")
    cf.stakeManager.stake(JUNK_INT, MIN_STAKE, NON_ZERO_ADDR, {'from': ALICE})

    claim_amount = int(MIN_STAKE / 3)
    print(f"\n💰 Alice registers a claim for {claim_amount} with nodeID {JUNK_INT}\n")
    args = (JUNK_INT, claim_amount, ALICE, chain.time()+(2*CLAIM_DELAY))
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(agg_null_sig(), *args)
    cf.stakeManager.registerClaim(AGG_SIGNER_1.getSigData(callDataNoSig), *args)

    chain.sleep(CLAIM_DELAY)

    print(f"\n💰 Alice executes a claim for nodeID {JUNK_INT}\n")
    cf.stakeManager.executeClaim(JUNK_INT)

    new_min_stake = int(MIN_STAKE / 3)
    print(f"\n💰 Denice sets the minimum stake to {new_min_stake}\n")
    callDataNoSig = cf.stakeManager.setMinStake.encode_input(gov_null_sig(), new_min_stake)
    cf.stakeManager.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), new_min_stake, {"from": DENICE})

    stateChainBlockNumber = 100
    print(f"\n💰 Denice sets the new total supply to {NEW_TOTAL_SUPPLY_MINT} at state chain block 100\n")
    callDataNoSig = cf.stakeManager.updateFlipSupply.encode_input(agg_null_sig(), NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber)
    cf.stakeManager.updateFlipSupply(AGG_SIGNER_1.getSigData(callDataNoSig), NEW_TOTAL_SUPPLY_MINT, stateChainBlockNumber, {"from": DENICE})

def all_keyManager_events():
    print(f"\n🔑 Aggregate Key sets the new Aggregate Key 🔑\n")
    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(agg_null_sig(), AGG_SIGNER_2.getPubData())
    cf.keyManager.setAggKeyWithAggKey(AGG_SIGNER_1.getSigData(callDataNoSig), AGG_SIGNER_2.getPubData())

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Governance Key sets the new Aggregate Key 🔑\n")
    callDataNoSig = cf.keyManager.setAggKeyWithGovKey.encode_input(gov_null_sig(), AGG_SIGNER_1.getPubData())
    cf.keyManager.setAggKeyWithGovKey(GOV_SIGNER_1.getSigData(callDataNoSig), AGG_SIGNER_1.getPubData())

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Governance Key sets the new Governance Key 🔑\n")
    callDataNoSig = cf.keyManager.setGovKeyWithGovKey.encode_input(gov_null_sig(), GOV_SIGNER_2.getPubData())
    cf.keyManager.setGovKeyWithGovKey(GOV_SIGNER_1.getSigData(callDataNoSig), GOV_SIGNER_2.getPubData())
