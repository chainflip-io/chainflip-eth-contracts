from consts import *
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import strategy, contract_strategy
from utils import *
from hypothesis import strategies as hypStrat
from random import choice, choices
import random

settings = {"stateful_step_count": 100, "max_examples": 50}


# Stateful test for testing contract upgrades
def test_upgradability(
    BaseStateMachine, state_machine, a, cf, StakeManager, KeyManager, Vault
):
    class StateMachine(BaseStateMachine):

        # Max funds in the Vault
        TOTAL_FUNDS = 10**3 * E_18

        """
        This test deploys a new version of the following contracts: StakeManager, Vault and KeyManager

        All the references to these contracts need to be updated in the already deployed contracts.
        """

        # Set up the initial test conditions once
        def __init__(cls, a, cf, StakeManager, KeyManager, Vault):
            super().__init__(cls, a, cf)
            cls.totalFlipstaked = cf.flip.balanceOf(cf.stakeManager)

            # Store original contracts to be able to test upgradability
            cls.orig_sm = cls.sm
            cls.orig_v = cls.v
            cls.orig_km = cls.km

        # Reset the local versions of state to compare the contract to after every run
        def setup(self):
            # Set original contracts to be able to test upgradability
            self.sm = self.orig_sm
            self.v = self.orig_v
            self.km = self.orig_km

            self.lastValidateTime = self.km.tx.timestamp
            self.numTxsTested = 0

            # StakeManager
            self.lastSupplyBlockNumber = 0
            self.sm_communityKey = self.sm.getCommunityKey()
            self.sm_guard = self.sm.getCommunityGuard()
            self.sm_suspended = self.sm.getSuspendedState()

            # Vault - initialize with some funds
            a[3].transfer(self.v, self.TOTAL_FUNDS)
            self.v_communityKey = self.v.getCommunityKey()
            self.v_guard = self.v.getCommunityGuard()
            self.v_suspended = self.v.getSuspendedState()

        # Variables that will be a random value with each fcn/rule called

        st_sender = strategy("address")
        st_vault_transfer_amount = strategy("uint", max_value=TOTAL_FUNDS, exclude=0)
        st_sleep_time = strategy("uint", max_value=7 * DAY)

        # Deploys a new keyManager and updates all the references to it
        def rule_upgrade_keyManager(self, st_sender):
            aggKeyNonceConsumers = [self.f, self.sm, self.v]

            # Reusing current keyManager aggregateKey for simplicity
            newKeyManager = st_sender.deploy(
                KeyManager, self.km.getAggregateKey(), st_sender, cf.communityKey
            )

            keyManagerAddress = random.choice([newKeyManager, self.km])

            toWhitelist = [self.v, self.sm, self.f, keyManagerAddress]

            if keyManagerAddress == self.km:
                with reverts(REV_MSG_KEYMANAGER_WHITELIST):
                    print(
                        "        REV_MSG_SIG rule_upgrade_keyManager",
                        st_sender,
                        keyManagerAddress.address,
                    )
                    newKeyManager.setCanConsumeKeyNonce(
                        toWhitelist, {"from": st_sender}
                    )
            else:
                print(
                    "                    rule_upgrade_keyManager",
                    st_sender,
                    keyManagerAddress.address,
                )
                newKeyManager.setCanConsumeKeyNonce(toWhitelist, {"from": st_sender})

                for aggKeyNonceConsumer in aggKeyNonceConsumers:
                    assert aggKeyNonceConsumer.getKeyManager() == self.km

                    callDataNoSig = aggKeyNonceConsumer.updateKeyManager.encode_input(
                        agg_null_sig(self.km, chain.id), newKeyManager
                    )

                    aggKeyNonceConsumer.updateKeyManager(
                        AGG_SIGNER_1.getSigData(callDataNoSig, self.km),
                        newKeyManager,
                    )
                    assert aggKeyNonceConsumer.getKeyManager() == newKeyManager

                self.km = newKeyManager
                self.lastValidateTime = self.km.tx.timestamp

        # Deploys a new Vault and transfers the funds from the old Vault to the new one
        def rule_upgrade_Vault(
            self, st_sender, st_vault_transfer_amount, st_sleep_time
        ):

            newVault = st_sender.deploy(Vault, self.km)

            # Keep old Vault whitelisted
            currentWhitelist = [
                self.v,
                self.sm,
                self.f,
                self.km,
            ]
            toWhitelist = [
                self.v,
                self.sm,
                self.f,
                self.km,
                newVault,
            ]
            updateCanConsumeKeyNonce(self.km, currentWhitelist, toWhitelist, cf.ALICE)

            # Vault can now validate and fetch but it has zero balance so it can't transfer
            callDataNoSig = newVault.transfer.encode_input(
                agg_null_sig(self.km.address, chain.id),
                ETH_ADDR,
                st_sender,
                st_vault_transfer_amount,
            )
            tx = newVault.transfer(
                AGG_SIGNER_1.getSigData(callDataNoSig, self.km.address),
                ETH_ADDR,
                st_sender,
                st_vault_transfer_amount,
            )
            assert tx.events["TransferFailed"][0].values() == [
                st_sender,
                st_vault_transfer_amount,
                web3.toHex(0),
            ]

            # Transfer from oldVault to new Vault - unclear if we want to transfer all the balance
            startBalVault = self.v.balance()
            assert startBalVault >= st_vault_transfer_amount
            startBalRecipient = newVault.balance()

            callDataNoSig = self.v.transfer.encode_input(
                agg_null_sig(self.km.address, chain.id),
                ETH_ADDR,
                newVault,
                st_vault_transfer_amount,
            )
            self.v.transfer(
                AGG_SIGNER_1.getSigData(callDataNoSig, self.km.address),
                ETH_ADDR,
                newVault,
                st_vault_transfer_amount,
            )

            assert self.v.balance() - startBalVault == -st_vault_transfer_amount
            assert newVault.balance() - startBalRecipient == st_vault_transfer_amount

            chain.sleep(st_sleep_time)

            # Transfer all the remaining funds to new Vault and dewhitelist
            startBalVault = self.v.balance()
            startBalRecipient = newVault.balance()

            if st_vault_transfer_amount > self.v.balance():
                print(
                    "        TRANSF_FAIL rule_upgrade_vault",
                    st_sender,
                    st_vault_transfer_amount,
                )
                callDataNoSig = self.v.transfer.encode_input(
                    agg_null_sig(self.km.address, chain.id),
                    ETH_ADDR,
                    newVault,
                    st_vault_transfer_amount,
                )
                tx = self.v.transfer(
                    AGG_SIGNER_1.getSigData(callDataNoSig, self.km.address),
                    ETH_ADDR,
                    newVault,
                    st_vault_transfer_amount,
                )
                assert tx.events["TransferFailed"][0].values() == [
                    newVault.address,
                    st_vault_transfer_amount,
                    web3.toHex(0),
                ]
            print(
                "                    rule_upgrade_vault",
                st_sender,
                st_vault_transfer_amount,
            )
            # Transfer all the remainding balance
            amountToTransfer = self.v.balance()
            callDataNoSig = self.v.transfer.encode_input(
                agg_null_sig(self.km.address, chain.id),
                ETH_ADDR,
                newVault,
                amountToTransfer,
            )
            self.v.transfer(
                AGG_SIGNER_1.getSigData(callDataNoSig, self.km.address),
                ETH_ADDR,
                newVault,
                amountToTransfer,
            )

            assert self.v.balance() - startBalVault == -amountToTransfer
            assert newVault.balance() - startBalRecipient == amountToTransfer
            assert newVault.balance() == self.TOTAL_FUNDS

            # Dewhitelist old Vault
            currentWhitelist = [
                self.v,
                self.sm,
                self.f,
                self.km,
                newVault,
            ]
            toWhitelist = [self.sm, self.f, self.km, newVault]
            updateCanConsumeKeyNonce(self.km, currentWhitelist, toWhitelist, cf.ALICE)

            self.v = newVault
            self.lastValidateTime = tx.timestamp
            self.v_communityKey = self.communityKey
            self.v_guard = False
            self.v_suspended = False

        # Deploys a new Stake Manager and transfers the FLIP tokens from the old SM to the new one
        def rule_upgrade_stakeManager(
            self, st_sender, st_vault_transfer_amount, st_sleep_time
        ):
            newStakeManager = st_sender.deploy(
                StakeManager,
                self.km,
                MIN_STAKE,
            )

            newStakeManager.setFlip(self.f, {"from": st_sender})

            # Keep old StakeManager whitelisted
            currentWhitelist = [
                self.v,
                self.sm,
                self.f,
                self.km,
            ]
            toWhitelist = [
                self.v,
                self.sm,
                self.f,
                self.km,
                newStakeManager,
            ]
            updateCanConsumeKeyNonce(self.km, currentWhitelist, toWhitelist, cf.ALICE)

            chain.sleep(st_sleep_time)

            # Generate claim to move all FLIP to new stakeManager
            stakeAmount = MIN_STAKE
            expiryTime = getChainTime() + (CLAIM_DELAY * 10)
            claimAmount = self.totalFlipstaked
            # Register Claim to transfer all flip
            callDataNoSig = self.sm.registerClaim.encode_input(
                agg_null_sig(self.km.address, chain.id),
                JUNK_HEX,
                claimAmount,
                newStakeManager,
                expiryTime,
            )
            tx = self.sm.registerClaim(
                AGG_SIGNER_1.getSigData(callDataNoSig, self.km.address),
                JUNK_HEX,
                claimAmount,
                newStakeManager,
                expiryTime,
            )

            chain.sleep(st_sleep_time)
            if st_sleep_time < CLAIM_DELAY:
                with reverts(REV_MSG_NOT_ON_TIME):
                    print(
                        "        REV_MSG_SIG rule_upgrade_stakeManager", st_sleep_time
                    )
                    self.sm.executeClaim(JUNK_HEX)

            chain.sleep(CLAIM_DELAY * 2)

            print("                   rule_executeClaim", newStakeManager.address)
            assert self.f.balanceOf(newStakeManager) == 0
            assert self.f.balanceOf(self.sm) == self.totalFlipstaked

            self.sm.executeClaim(JUNK_HEX, {"from": st_sender})

            assert self.f.balanceOf(newStakeManager) == self.totalFlipstaked
            assert self.f.balanceOf(self.sm) == 0

            # Dewhitelist old StakeManager
            currentWhitelist = [
                self.v,
                self.sm,
                self.f,
                self.km,
                newStakeManager,
            ]
            toWhitelist = [self.v, newStakeManager, self.f, self.km]
            updateCanConsumeKeyNonce(self.km, currentWhitelist, toWhitelist, cf.ALICE)

            self.sm = newStakeManager
            self.sm_communityKey = self.communityKey
            self.sm_guard = False
            self.sm_suspended = False

        # Check that all the funds (ETH and FLIP) total amounts have not changed and have been transferred
        def invariant_bals(self):
            self.numTxsTested += 1
            assert self.v.balance() == self.TOTAL_FUNDS
            assert self.f.balanceOf(self.sm) == self.totalFlipstaked

        # KeyManager might have changed but references must be updated
        # FLIP contract should have remained the same
        def invariant_state_vars(self):
            assert self.v.getKeyManager() == self.km.address
            assert self.sm.getKeyManager() == self.km.address
            assert self.f.getKeyManager() == self.km.address

            assert self.sm.getFLIP() == self.f.address
            assert self.f.getLastSupplyUpdateBlockNumber() == self.lastSupplyBlockNumber

        def invariant_governanceCommunityGuard(self):
            assert self.v_communityKey == self.v.getCommunityKey()
            assert self.v_guard == self.v.getCommunityGuard()
            assert self.v_suspended == self.v.getSuspendedState()
            assert self.sm_communityKey == self.sm.getCommunityKey()
            assert self.sm_guard == self.sm.getCommunityGuard()
            assert self.sm_suspended == self.sm.getSuspendedState()

        def invariant_keyManager_whitelist(self):
            aggKeyNonceConsumers = [
                self.km,
                self.v,
                self.f,
                self.sm,
            ]
            assert self.km.getNumberWhitelistedAddresses() == len(aggKeyNonceConsumers)

            for aggKeyNonceConsumer in aggKeyNonceConsumers:
                assert self.km.canConsumeKeyNonce(aggKeyNonceConsumer.address) == True

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f"Total rules executed = {self.numTxsTested-1}")

    state_machine(
        StateMachine,
        a,
        cf,
        StakeManager,
        KeyManager,
        Vault,
        settings=settings,
    )
