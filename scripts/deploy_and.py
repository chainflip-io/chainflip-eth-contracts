import sys
from os import path

sys.path.append(path.abspath("tests"))
from consts import *
from brownie import (
    chain,
    accounts,
    KeyManager,
    Vault,
    StakeManager,
    FLIP,
    chain,
    network,
)
from deploy import deploy_set_Chainflip_contracts

print(network.show_active())

DEPLOYER = accounts[0]
ALICE = accounts[1]
BOB = accounts[2]
CHARLIE = accounts[3]
DENICE = accounts[4]
GOVERNOR = accounts[0]
GOVERNOR_2 = accounts[5]

cf = deploy_set_Chainflip_contracts(
    DEPLOYER, KeyManager, Vault, StakeManager, FLIP, {"PREFUND_CONTRACTS": "False"}
)

cf.flip.transfer(ALICE, MAX_TEST_STAKE, {"from": DEPLOYER})
cf.flip.approve(cf.stakeManager, MAX_TEST_STAKE, {"from": ALICE})
cf.flip.transfer(BOB, MAX_TEST_STAKE, {"from": DEPLOYER})
cf.flip.approve(cf.stakeManager, MAX_TEST_STAKE, {"from": BOB})

print("========================= 😎  Deployed! 😎 ==========================\n")
print(f"KeyManager deployed by {DEPLOYER} to address: {cf.keyManager.address}\n")
print(f"Vault deployed by {DEPLOYER} to address: {cf.vault.address}\n")
print(f"StakeManager deployed by {DEPLOYER} to address: {cf.stakeManager.address}\n")
print(f"FLIP deployed by {DEPLOYER} to address: {cf.flip.address}\n")
print("======================================================================")


def main():
    print()


def all_events():
    print(f"\n-- Stake Manager Events --\n")
    all_stakeManager_events()
    chain.sleep(CLAIM_DELAY)
    print(f"\n-- Key Manager Events --\n")
    all_keyManager_events()


def all_stakeManager_events():
    print(f"\n💰 Alice stakes {MIN_STAKE} with nodeID {JUNK_INT}\n")
    cf.stakeManager.stake(JUNK_INT, MIN_STAKE, NON_ZERO_ADDR, {"from": ALICE})

    claim_amount = int(MIN_STAKE / 3)
    print(f"\n💰 Alice registers a claim for {claim_amount} with nodeID {JUNK_INT}\n")
    args = (JUNK_INT, claim_amount, ALICE, chain.time() + (2 * CLAIM_DELAY))
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    cf.stakeManager.registerClaim(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), *args
    )

    chain.sleep(CLAIM_DELAY)

    print(f"\n💰 Alice executes a claim for nodeID {JUNK_INT}\n")
    cf.stakeManager.executeClaim(JUNK_INT)

    new_min_stake = int(MIN_STAKE / 3)
    print(f"\n💰 Denice sets the minimum stake to {new_min_stake}\n")
    print("This transaction will emit RefundFailed")
    cf.stakeManager.setMinStake(new_min_stake, {"from": GOVERNOR})

    print("Fund contract so that a refund will fire in the next transaction")
    ALICE.transfer(to=cf.stakeManager, amount=ONE_ETH)

    stateChainBlockNumber = 100
    print(
        f"\n💰 Denice sets the new total supply to {NEW_TOTAL_SUPPLY_MINT} at state chain block {stateChainBlockNumber}\n"
    )
    callDataNoSig = cf.stakeManager.updateFlipSupply.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    )
    cf.stakeManager.updateFlipSupply(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        {"from": DENICE},
    )

    print(f"\n🔐 Governnace suspends execution of claims\n")
    cf.stakeManager.suspend({"from": GOVERNOR})

    print(f"\n💸 Governance withdraws all FLIP\n")
    cf.stakeManager.govWithdraw({"from": GOVERNOR})


def all_keyManager_events():
    print(f"\n🔑 Governance Key sets the new Aggregate Key 🔑\n")
    cf.keyManager.setAggKeyWithGovKey(AGG_SIGNER_1.getPubData(), {"from": GOVERNOR})

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Governance Key sets the new Governance Key 🔑\n")
    cf.keyManager.setGovKeyWithGovKey(GOVERNOR_2, {"from": GOVERNOR})

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Aggregate Key 🔑\n")
    print("This transaction will emit RefundFailed")
    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), AGG_SIGNER_2.getPubData()
    )
    cf.keyManager.setAggKeyWithAggKey(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        AGG_SIGNER_2.getPubData(),
    )

    chain.sleep(CLAIM_DELAY)

    print("Fund contract so that a refund event will fire in the next transaction")
    ALICE.transfer(to=cf.keyManager, amount=ONE_ETH)

    print(f"\n🔑 Aggregate Key sets the new Aggregate Key 🔑\n")
    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), AGG_SIGNER_1.getPubData()
    )
    cf.keyManager.setAggKeyWithAggKey(
        AGG_SIGNER_2.getSigData(callDataNoSig, cf.keyManager.address),
        AGG_SIGNER_1.getPubData(),
    )
