import sys
from os import path

sys.path.append(path.abspath("tests"))
from shared_tests import *
from consts import *
from brownie import (
    chain,
    accounts,
    KeyManager,
    Vault,
    StateChainGateway,
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
    DEPLOYER, KeyManager, Vault, StateChainGateway, FLIP, DeployerContract
)

cf.flip.transfer(ALICE, MAX_TEST_FUND, {"from": cf.safekeeper})
cf.flip.approve(cf.stateChainGateway, MAX_TEST_FUND, {"from": ALICE})
cf.flip.transfer(BOB, MAX_TEST_FUND, {"from": cf.safekeeper})
cf.flip.approve(cf.stateChainGateway, MAX_TEST_FUND, {"from": BOB})


def main():
    print()


def all_events():
    print(f"\n-- FLIP Events --\n")
    all_flip_events()
    print(f"\n-- State Chain Gateway Events --\n")
    all_stateChainGateway_events()
    chain.sleep(REDEMPTION_DELAY)
    print(f"\n-- Vault Events --\n")
    all_vault_events()
    print(f"\n-- Key Manager Events --\n")
    all_keyManager_events()

    print("========================= 😎  Deployed! 😎 ==========================\n")
    print(f"Deployer: {DEPLOYER}\n")
    print(f"KeyManager: {cf.keyManager.address}\n")
    print(f"Vault: {cf.vault.address}\n")
    print(f"StateChainGateway: {cf.stateChainGateway.address}\n")
    print(f"FLIP: {cf.flip.address}\n")
    print("======================================================================")


def all_stateChainGateway_events():
    print(f"\n💰 Alice funds with {MIN_FUNDING} with nodeID {JUNK_INT}\n")
    cf.stateChainGateway.fundStateChainAccount(
        JUNK_INT, MIN_FUNDING, NON_ZERO_ADDR, {"from": ALICE}
    )

    redemption_amount = int(MIN_FUNDING / 3)
    print(
        f"\n💰 Alice registers a redemption for {redemption_amount} with nodeID {JUNK_INT}\n"
    )
    args = (JUNK_INT, redemption_amount, ALICE, chain.time() + (2 * REDEMPTION_DELAY))

    signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args, sender=ALICE)

    chain.sleep(REDEMPTION_DELAY)

    print(f"\n💰 Alice executes a redemption for nodeID {JUNK_INT}\n")
    cf.stateChainGateway.executeRedemption(JUNK_INT, {"from": ALICE})

    args = (JUNK_INT, redemption_amount, ALICE, chain.time() + (2 * REDEMPTION_DELAY))

    signed_call_cf(cf, cf.stateChainGateway.registerRedemption, *args, sender=ALICE)

    chain.sleep(REDEMPTION_DELAY * 3)
    print(f"\n💰 Alice executes a redemption after expiry for nodeID {JUNK_INT}\n")
    cf.stateChainGateway.executeRedemption(JUNK_INT, {"from": ALICE})

    stateChainBlockNumber = 100
    print(
        f"\n💰 Denice sets the new total supply to {NEW_TOTAL_SUPPLY_MINT} at state chain block {stateChainBlockNumber}\n"
    )

    signed_call(
        cf.keyManager,
        cf.stateChainGateway.updateFlipSupply,
        AGG_SIGNER_1,
        DENICE,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    )

    new_MIN_FUNDING = int(MIN_FUNDING / 3)
    print(f"\n💰 Denice sets the minimum funding to {new_MIN_FUNDING}\n")
    cf.stateChainGateway.setMinFunding(new_MIN_FUNDING, {"from": GOVERNOR})

    print(f"\n🔐 Governance suspends execution of redemptions\n")
    cf.stateChainGateway.suspend({"from": GOVERNOR})

    print(f"\n🔐 Community disables guard\n")
    cf.stateChainGateway.disableCommunityGuard({"from": cf.communityKey})

    print(f"\n💸 Governance withdraws all FLIP\n")
    cf.stateChainGateway.govWithdraw({"from": GOVERNOR})

    print(f"\n🔐 Community enables guard\n")
    cf.stateChainGateway.enableCommunityGuard({"from": cf.communityKey})

    print(f"\n🔐 Governance resumes execution of redemptions\n")
    cf.stateChainGateway.resume({"from": GOVERNOR})

    # Last StateChainGateway event to emit because we set a wrong new KeyManager address

    print(f"\n🔑 Update the keyManager address in State Chain Gateway🔑\n")

    signed_call_cf(
        cf, cf.stateChainGateway.updateKeyManager, NON_ZERO_ADDR, sender=ALICE
    )


def all_keyManager_events():
    # KeyNonceConsumersSet and setFlip events have already been emitted in the deployment script

    chain.sleep(AGG_KEY_TIMEOUT)

    print(f"\n🔑 Governance Key sets the new Aggregate Key 🔑\n")
    cf.keyManager.setAggKeyWithGovKey(AGG_SIGNER_1.getPubData(), {"from": GOVERNOR})

    chain.sleep(REDEMPTION_DELAY)

    print(f"\n🔑 Governance Key sets the new Governance Key 🔑\n")
    cf.keyManager.setGovKeyWithGovKey(GOVERNOR_2, {"from": GOVERNOR})

    chain.sleep(REDEMPTION_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Aggregate Key 🔑\n")

    signed_call(
        cf.keyManager,
        cf.keyManager.setAggKeyWithAggKey,
        AGG_SIGNER_1,
        ALICE,
        AGG_SIGNER_2.getPubData(),
    )

    chain.sleep(REDEMPTION_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Aggregate Key 🔑\n")

    signed_call(
        cf.keyManager,
        cf.keyManager.setAggKeyWithAggKey,
        AGG_SIGNER_2,
        ALICE,
        AGG_SIGNER_1.getPubData(),
    )

    chain.sleep(REDEMPTION_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Governance Key 🔑\n")

    signed_call(
        cf.keyManager, cf.keyManager.setGovKeyWithAggKey, AGG_SIGNER_1, ALICE, GOVERNOR
    )

    chain.sleep(REDEMPTION_DELAY)

    print(f"\n🔑 Community Key sets the new Community Key 🔑\n")
    cf.keyManager.setCommKeyWithCommKey(COMMUNITY_KEY_2, {"from": COMMUNITY_KEY})

    chain.sleep(REDEMPTION_DELAY)

    print(f"\n🔑 Aggregate Key sets the new Community Key 🔑\n")

    signed_call(
        cf.keyManager,
        cf.keyManager.setCommKeyWithAggKey,
        AGG_SIGNER_1,
        ALICE,
        COMMUNITY_KEY,
    )

    chain.sleep(REDEMPTION_DELAY)

    print(f"\n🔐 Governance calls for an action\n")

    cf.keyManager.govAction(JUNK_HEX, {"from": GOVERNOR})


def all_flip_events():
    print(f"\n🔑 Update the FLIP issuer in FLIP via the State Chain Gateway🔑\n")

    signed_call(
        cf.keyManager,
        cf.stateChainGateway.updateFlipIssuer,
        AGG_SIGNER_1,
        DENICE,
        cf.stateChainGateway.address,
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

    signed_call(cf.keyManager, cf.vault.transfer, AGG_SIGNER_1, ALICE, *args)

    transferFailureAmount = cf.flip.balanceOf(cf.vault) + 1
    print(
        f"\n❌ Failed transfer of {transferFailureAmount} token {cf.flip} to recipient {NON_ZERO_ADDR} with reason 0x08c379a0....00000\n"
    )
    args = [[cf.flip, NON_ZERO_ADDR, transferFailureAmount]]
    signed_call(cf.keyManager, cf.vault.transfer, AGG_SIGNER_1, ALICE, *args)

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

    signed_call(cf.keyManager, cf.vault.transferBatch, AGG_SIGNER_1, ALICE, *args)

    print(f"\n🔐 Governance suspends execution of redemptions\n")
    cf.vault.suspend({"from": GOVERNOR})

    print(f"\n🔐 Community disables guard\n")
    cf.vault.disableCommunityGuard({"from": cf.communityKey})

    chain.sleep(AGG_KEY_EMERGENCY_TIMEOUT)

    print(f"\n💸 Governance withdraws all NATIVE and FLIP\n")
    cf.vault.govWithdraw([NATIVE_ADDR, cf.flip], {"from": GOVERNOR})

    print(f"\n🔐 Community enables guard\n")
    cf.vault.enableCommunityGuard({"from": cf.communityKey})

    print(f"\n🔐 Governance resumes execution of redemptions\n")
    cf.vault.resume({"from": GOVERNOR})

    print(f"\n🔑 Update the keyManager address in the Vault🔑\n")

    signed_call(
        cf.keyManager, cf.vault.updateKeyManager, AGG_SIGNER_1, ALICE, NON_ZERO_ADDR
    )
