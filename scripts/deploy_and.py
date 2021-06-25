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

    new_emission_per_block = int(EMISSION_PER_BLOCK / 3)
    print(f"\n💰 Denice sets the new emission per block to {new_emission_per_block}\n")
    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(gov_null_sig(), new_emission_per_block)
    cf.stakeManager.setEmissionPerBlock(GOV_SIGNER_1.getSigData(callDataNoSig), new_emission_per_block, {"from": DENICE})