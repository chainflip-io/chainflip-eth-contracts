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
COMMUNITY_KEY = accounts[6]
COMMUNITY_KEY_2 = accounts[7]


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
    print(f"\n-- Vault Events --\n")
    all_vault_events()
    print(f"\n-- FLIP Events --\n")
    all_flip_events()
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
    cf.stakeManager.setMinStake(new_min_stake, {"from": GOVERNOR})

    print(f"\n🔐 Governance suspends execution of claims\n")
    cf.stakeManager.suspend({"from": GOVERNOR})

    print(f"\n🔐 Community disables guard\n")
    cf.stakeManager.disableCommunityGuard({"from": cf.communityKey})

    print(f"\n💸 Governance withdraws all FLIP\n")
    cf.stakeManager.govWithdraw({"from": GOVERNOR})

    print(f"\n🔐 Community enables guard\n")
    cf.stakeManager.enableCommunityGuard({"from": cf.communityKey})

    print(f"\n🔐 Governance resumes execution of claims\n")
    cf.stakeManager.resume({"from": GOVERNOR})

    # Last StakeManager event to emit because we set a wrong new KeyManager address

    print(f"\n🔑 Update the keyManager address in Stake Manager🔑\n")
    callDataNoSig = cf.stakeManager.updateKeyManager.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), NON_ZERO_ADDR
    )
    cf.stakeManager.updateKeyManager(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        NON_ZERO_ADDR,
    )


def all_keyManager_events():
    # KeyNonceConsumersSet and setFlip events have already been emitted in the deployment script

    chain.sleep(AGG_KEY_TIMEOUT)

    print(f"\n🔑 Governance Key sets the new Aggregate Key 🔑\n")
    cf.keyManager.setAggKeyWithGovKey(AGG_SIGNER_1.getPubData(), {"from": GOVERNOR})

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Governance Key sets the new Governance Key 🔑\n")
    cf.keyManager.setGovKeyWithGovKey(GOVERNOR_2, {"from": GOVERNOR})

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Aggregate Key 🔑\n")
    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), AGG_SIGNER_2.getPubData()
    )
    cf.keyManager.setAggKeyWithAggKey(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        AGG_SIGNER_2.getPubData(),
    )

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Aggregate Key 🔑\n")
    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), AGG_SIGNER_1.getPubData()
    )
    cf.keyManager.setAggKeyWithAggKey(
        AGG_SIGNER_2.getSigData(callDataNoSig, cf.keyManager.address),
        AGG_SIGNER_1.getPubData(),
    )

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Governance Key 🔑\n")
    callDataNoSig = cf.keyManager.setGovKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), GOVERNOR
    )
    cf.keyManager.setGovKeyWithAggKey(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        GOVERNOR,
    )

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Community Key sets the new Community Key 🔑\n")
    cf.keyManager.setCommKeyWithCommKey(COMMUNITY_KEY_2, {"from": COMMUNITY_KEY})

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Community Key 🔑\n")
    callDataNoSig = cf.keyManager.setCommKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), COMMUNITY_KEY
    )
    cf.keyManager.setCommKeyWithAggKey(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        COMMUNITY_KEY,
    )

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔐 Governance calls for an action\n")

    cf.keyManager.govAction(JUNK_HEX, {"from": GOVERNOR})

    print(f"\n🔑 Update the Key Nonce Consumer list (whitelist) 🔑\n")
    callDataNoSig = cf.keyManager.updateCanConsumeKeyNonce.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), cf.whitelisted, cf.whitelisted
    )
    cf.keyManager.updateCanConsumeKeyNonce(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        cf.whitelisted,
        cf.whitelisted,
    )


def all_flip_events():
    stateChainBlockNumber = 100
    print(
        f"\n💰 Denice sets the new total supply to {NEW_TOTAL_SUPPLY_MINT} at state chain block {stateChainBlockNumber}\n"
    )
    callDataNoSig = cf.flip.updateFlipSupply.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        cf.stakeManager.address,
    )
    cf.flip.updateFlipSupply(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        cf.stakeManager.address,
        {"from": DENICE},
    )

    print(f"\n🔑 Update the keyManager address in FLIP🔑\n")
    callDataNoSig = cf.flip.updateKeyManager.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), NON_ZERO_ADDR
    )
    cf.flip.updateKeyManager(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        NON_ZERO_ADDR,
    )


def all_vault_events():
    print(f"\n🔐 Enable Vault xCalls\n")
    cf.vault.enablexCalls({"from": GOVERNOR})

    print(
        f"\n💰 Alice xCalls with message {JUNK_HEX} to destination address {JUNK_STR}, dstChain {JUNK_INT}, swaps {TEST_AMNT} ETH, swapIntent USDC and refund Address {ALICE}\n"
    )
    cf.vault.xCallNative(
        JUNK_INT, JUNK_STR, "USDC", JUNK_HEX, ALICE, {"amount": TEST_AMNT}
    )

    print(
        f"\n💰 Alice xCalls with message {JUNK_HEX} to destination address {JUNK_STR}, dstChain {JUNK_INT}, swaps {TEST_AMNT} IngressToken {cf.flip}, swapIntent USDC and refund Address {ALICE}\n"
    )
    cf.flip.approve(cf.vault, TEST_AMNT)
    cf.vault.xCallToken(JUNK_INT, JUNK_STR, "USDC", JUNK_HEX, cf.flip, TEST_AMNT, ALICE)

    print(f"\n🔐 Disable Vault xCalls\n")
    cf.vault.disablexCalls({"from": GOVERNOR})

    print(
        f"\n💰 Alice swaps {TEST_AMNT} ETH with swapIntent BTC, destination address {JUNK_STR} and dstChain {JUNK_INT}\n"
    )
    cf.vault.xSwapNative(JUNK_INT, JUNK_STR, "BTC", {"amount": TEST_AMNT})

    print(
        f"\n💰 Alice swaps {TEST_AMNT} IngressToken {cf.flip} swapIntent BTC, destination address {JUNK_STR} and dstChain {JUNK_INT}\n"
    )
    cf.flip.approve(cf.vault, TEST_AMNT)
    cf.vault.xSwapToken(
        JUNK_INT,
        JUNK_STR,
        "BTC",
        cf.flip,
        TEST_AMNT,
    )

    print(f"\n🔐 Governance suspends execution of claims\n")
    cf.vault.suspend({"from": GOVERNOR})

    print(f"\n🔐 Community disables guard\n")
    cf.vault.disableCommunityGuard({"from": cf.communityKey})

    chain.sleep(AGG_KEY_EMERGENCY_TIMEOUT)

    print(f"\n💸 Governance withdraws all NATIVE and FLIP\n")
    cf.vault.govWithdraw([NATIVE_ADDR, cf.flip], {"from": GOVERNOR})

    print(f"\n🔐 Community enables guard\n")
    cf.vault.enableCommunityGuard({"from": cf.communityKey})

    print(f"\n🔐 Governance resumes execution of claims\n")
    cf.vault.resume({"from": GOVERNOR})

    print(f"\n🔑 Update the keyManager address in the Vault🔑\n")
    callDataNoSig = cf.vault.updateKeyManager.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), NON_ZERO_ADDR
    )
    cf.vault.updateKeyManager(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        NON_ZERO_ADDR,
    )
