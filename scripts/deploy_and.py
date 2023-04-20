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
    DeployerContract,
    chain,
    network,
)
from deploy import deploy_Chainflip_contracts

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


cf = deploy_Chainflip_contracts(
    DEPLOYER, KeyManager, Vault, StakeManager, FLIP, DeployerContract
)

cf.flip.transfer(ALICE, MAX_TEST_STAKE, {"from": cf.safekeeper})
cf.flip.approve(cf.stakeManager, MAX_TEST_STAKE, {"from": ALICE})
cf.flip.transfer(BOB, MAX_TEST_STAKE, {"from": cf.safekeeper})
cf.flip.approve(cf.stakeManager, MAX_TEST_STAKE, {"from": BOB})


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

    print("========================= 😎  Deployed! 😎 ==========================\n")
    print(f"Deployer: {DEPLOYER}\n")
    print(f"KeyManager: {cf.keyManager.address}\n")
    print(f"Vault: {cf.vault.address}\n")
    print(f"StakeManager: {cf.stakeManager.address}\n")
    print(f"FLIP: {cf.flip.address}\n")
    print("======================================================================")


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
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        *args,
        {"from": ALICE},
    )

    chain.sleep(CLAIM_DELAY)

    print(f"\n💰 Alice executes a claim for nodeID {JUNK_INT}\n")
    cf.stakeManager.executeClaim(JUNK_INT, {"from": ALICE})

    args = (JUNK_INT, claim_amount, ALICE, chain.time() + (2 * CLAIM_DELAY))
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    cf.stakeManager.registerClaim(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        *args,
        {"from": ALICE},
    )
    chain.sleep(CLAIM_DELAY * 3)
    print(f"\n💰 Alice executes a claim after expiry for nodeID {JUNK_INT}\n")
    cf.stakeManager.executeClaim(JUNK_INT, {"from": ALICE})

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
        {"from": ALICE},
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
        {"from": ALICE},
    )

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Aggregate Key 🔑\n")
    callDataNoSig = cf.keyManager.setAggKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), AGG_SIGNER_1.getPubData()
    )
    cf.keyManager.setAggKeyWithAggKey(
        AGG_SIGNER_2.getSigData(callDataNoSig, cf.keyManager.address),
        AGG_SIGNER_1.getPubData(),
        {"from": ALICE},
    )

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Governance Key 🔑\n")
    callDataNoSig = cf.keyManager.setGovKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), GOVERNOR
    )
    cf.keyManager.setGovKeyWithAggKey(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        GOVERNOR,
        {"from": ALICE},
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
        {"from": ALICE},
    )

    chain.sleep(CLAIM_DELAY)

    print(f"\n🔐 Governance calls for an action\n")

    cf.keyManager.govAction(JUNK_HEX, {"from": GOVERNOR})

    print(f"\n🔑 Update the Key Nonce Consumer list (whitelist) 🔑\n")
    cf.whitelisted = [
        cf.vault.address,
        cf.stakeManager.address,
        cf.flip.address,
    ]
    callDataNoSig = cf.keyManager.updateCanConsumeKeyNonce.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), cf.whitelisted, cf.whitelisted
    )
    cf.keyManager.updateCanConsumeKeyNonce(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        cf.whitelisted,
        cf.whitelisted,
        {"from": ALICE},
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
        {"from": DENICE},
    )


def all_vault_events():
    print(
        f"\n💰 Alice swaps {TEST_AMNT} ETH with dstToken 1, destination address {JUNK_HEX} and dstChain {JUNK_INT}\n"
    )
    cf.vault.xSwapNative(JUNK_INT, JUNK_HEX, 1, {"amount": TEST_AMNT, "from": ALICE})

    print(
        f"\n💰 Alice swaps {TEST_AMNT} IngressToken {cf.flip} dstToken 1, destination address {JUNK_HEX} and dstChain {JUNK_INT}\n"
    )
    cf.flip.approve(cf.vault, TEST_AMNT, {"from": ALICE})
    cf.vault.xSwapToken(
        JUNK_INT,
        JUNK_HEX,
        1,
        cf.flip,
        TEST_AMNT,
        {"from": ALICE},
    )

    print(
        f"\n💰 Alice xCalls with message {JUNK_HEX} to destination address {JUNK_HEX}, dstChain {JUNK_INT}, swaps {TEST_AMNT}, dstToken 3 and refund Address {JUNK_HEX}\n"
    )
    cf.vault.xCallNative(
        JUNK_INT,
        JUNK_HEX,
        3,
        JUNK_HEX,
        JUNK_INT,
        JUNK_HEX,
        {"amount": TEST_AMNT, "from": ALICE},
    )

    print(
        f"\n💰 Alice xCalls with message {JUNK_HEX} to destination address {JUNK_HEX}, dstChain {JUNK_INT}, swaps {TEST_AMNT}, IngressToken {cf.flip}, dstToken 3 and refund Address {JUNK_HEX}\n"
    )
    cf.flip.approve(cf.vault, TEST_AMNT, {"from": ALICE})
    cf.vault.xCallToken(
        JUNK_INT,
        JUNK_HEX,
        3,
        JUNK_HEX,
        JUNK_INT,
        cf.flip,
        TEST_AMNT,
        JUNK_HEX,
        {"from": ALICE},
    )

    print(f"\n💰 Alice adds {TEST_AMNT} ETH to the swap with swapID {JUNK_HEX}\n")
    cf.vault.addGasNative(JUNK_HEX, {"amount": TEST_AMNT, "from": ALICE})

    print(
        f"\n💰 Alice adds {TEST_AMNT} IngressToken {cf.flip} to the swap with swapID {JUNK_HEX}\n"
    )
    cf.flip.approve(cf.vault, TEST_AMNT, {"from": ALICE})
    cf.vault.addGasToken(JUNK_HEX, TEST_AMNT, cf.flip, {"from": ALICE})

    print(f"\n❌ Failed transfer of {TEST_AMNT} ETH to recipient {cf.flip}\n")
    args = [[NATIVE_ADDR, cf.flip, TEST_AMNT]]
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    cf.vault.transfer(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        *args,
        {"from": ALICE},
    )

    transferFailureAmount = cf.flip.balanceOf(cf.vault) + 1
    print(
        f"\n❌ Failed transfer of {transferFailureAmount} token {cf.flip} to recipient {NON_ZERO_ADDR} with reason 0x08c379a0....00000\n"
    )
    args = [[cf.flip, NON_ZERO_ADDR, transferFailureAmount]]
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    cf.vault.transfer(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        *args,
        {"from": ALICE},
    )

    print(
        f"\n❌ Failed batch transfer of 2x[{TEST_AMNT} ETH to recipient {cf.flip}] and 1x[{transferFailureAmount} token {cf.flip} to recipient {NON_ZERO_ADDR} with reason 0x08c379a0....00000]\n"
    )
    args = [
        [
            [NATIVE_ADDR, cf.flip, TEST_AMNT],
            [NATIVE_ADDR, cf.flip, TEST_AMNT],
            [cf.flip, NON_ZERO_ADDR, transferFailureAmount],
        ]
    ]
    callDataNoSig = cf.vault.transferBatch.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), *args
    )
    cf.vault.transferBatch(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        *args,
        {"from": ALICE},
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
        {"from": ALICE},
    )
