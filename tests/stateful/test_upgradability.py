from consts import *
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import strategy, contract_strategy
from utils import *
from hypothesis import strategies as hypStrat
from random import choice, choices
import pytest
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

        # Reset the local versions of state to compare the contract to after every run
        def setup(self):
            self.lastValidateTime = self.km.tx.timestamp
            self.numTxsTested = 0

            self.current_km = self.km
            self.current_sm = self.sm
            self.current_v = self.v

            # StakeManager
            self.lastSupplyBlockNumber = 0

            # Vault - initialize with some funds
            a[3].transfer(self.v, self.TOTAL_FUNDS)

        # Variables that will be a random value with each fcn/rule called

        st_sender = strategy("address")
        st_vault_transfer_amount = strategy("uint", max_value=TOTAL_FUNDS, exclude=0)
        st_sleep_time = strategy("uint", max_value=7 * DAY)

        # Deploys a new keyManager and updates all the references to it
        def rule_upgrade_keyManager(self, st_sender):
            aggKeyNonceConsumers = [self.f, self.current_sm, self.current_v]

            # Reusing current keyManager aggregateKey for simplicity
            newKeyManager = st_sender.deploy(
                KeyManager, self.current_km.getAggregateKey(), st_sender
            )

            keyManagerAddress = random.choice([newKeyManager, self.current_km])

            toWhitelist = [self.current_v, self.current_sm, self.f, keyManagerAddress]

            if keyManagerAddress == self.current_km:
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
                    assert aggKeyNonceConsumer.getKeyManager() == self.current_km

                    callDataNoSig = aggKeyNonceConsumer.updateKeyManager.encode_input(
                        agg_null_sig(self.current_km, chain.id), newKeyManager
                    )

                    aggKeyNonceConsumer.updateKeyManager(
                        AGG_SIGNER_1.getSigData(callDataNoSig, self.current_km),
                        newKeyManager,
                    )
                    assert aggKeyNonceConsumer.getKeyManager() == newKeyManager

                self.current_km = newKeyManager
                self.lastValidateTime = self.current_km.tx.timestamp

        # Deploys a new Vault and transfers the funds from the old Vault to the new one
        def rule_upgrade_Vault(
            self, st_sender, st_vault_transfer_amount, st_sleep_time
        ):

            newVault = st_sender.deploy(Vault, self.current_km)

            # Keep old Vault whitelisted
            currentWhitelist = [
                self.current_v,
                self.current_sm,
                self.f,
                self.current_km,
            ]
            toWhitelist = [
                self.current_v,
                self.current_sm,
                self.f,
                self.current_km,
                newVault,
            ]
            updateCanConsumeKeyNonce(self.current_km, currentWhitelist, toWhitelist)

            # Vault can now validate and fetch but it has zero balance so it can't transfer
            callDataNoSig = newVault.transfer.encode_input(
                agg_null_sig(self.current_km.address, chain.id),
                ETH_ADDR,
                st_sender,
                st_vault_transfer_amount,
            )
            tx = newVault.transfer(
                AGG_SIGNER_1.getSigData(callDataNoSig, self.current_km.address),
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
            startBalVault = self.current_v.balance()
            assert startBalVault >= st_vault_transfer_amount
            startBalRecipient = newVault.balance()

            callDataNoSig = self.current_v.transfer.encode_input(
                agg_null_sig(self.current_km.address, chain.id),
                ETH_ADDR,
                newVault,
                st_vault_transfer_amount,
            )
            self.current_v.transfer(
                AGG_SIGNER_1.getSigData(callDataNoSig, self.current_km.address),
                ETH_ADDR,
                newVault,
                st_vault_transfer_amount,
            )

            assert self.current_v.balance() - startBalVault == -st_vault_transfer_amount
            assert newVault.balance() - startBalRecipient == st_vault_transfer_amount

            chain.sleep(st_sleep_time)

            # Transfer all the remaining funds to new Vault and dewhitelist
            startBalVault = self.current_v.balance()
            startBalRecipient = newVault.balance()

            if st_vault_transfer_amount > self.current_v.balance():
                print(
                    "        TRANSF_FAIL rule_upgrade_vault",
                    st_sender,
                    st_vault_transfer_amount,
                )
                callDataNoSig = self.current_v.transfer.encode_input(
                    agg_null_sig(self.current_km.address, chain.id),
                    ETH_ADDR,
                    newVault,
                    st_vault_transfer_amount,
                )
                tx = self.current_v.transfer(
                    AGG_SIGNER_1.getSigData(callDataNoSig, self.current_km.address),
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
            amountToTransfer = self.current_v.balance()
            callDataNoSig = self.current_v.transfer.encode_input(
                agg_null_sig(self.current_km.address, chain.id),
                ETH_ADDR,
                newVault,
                amountToTransfer,
            )
            self.current_v.transfer(
                AGG_SIGNER_1.getSigData(callDataNoSig, self.current_km.address),
                ETH_ADDR,
                newVault,
                amountToTransfer,
            )
            callDataNoSig = self.current_v.transfer.encode_input(
                agg_null_sig(self.current_km.address, chain.id),
                ETH_ADDR,
                newVault,
                amountToTransfer,
            )
            assert self.current_v.balance() - startBalVault == -amountToTransfer
            assert newVault.balance() - startBalRecipient == amountToTransfer
            assert newVault.balance() == self.TOTAL_FUNDS

            # Dewhitelist old Vault
            currentWhitelist = [
                self.current_v,
                self.current_sm,
                self.f,
                self.current_km,
                newVault,
            ]
            toWhitelist = [self.current_sm, self.f, self.current_km, newVault]
            updateCanConsumeKeyNonce(self.current_km, currentWhitelist, toWhitelist)

            self.current_v = newVault
            self.lastValidateTime = tx.timestamp

        # Deploys a new Stake Manager and transfers the FLIP tokens from the old SM to the new one
        def rule_upgrade_stakeManager(
            self, st_sender, st_vault_transfer_amount, st_sleep_time
        ):
            newStakeManager = st_sender.deploy(
                StakeManager,
                self.current_km,
                MIN_STAKE,
            )

            newStakeManager.setFlip(self.f, {"from": st_sender})

            # Keep old StakeManager whitelisted
            currentWhitelist = [
                self.current_v,
                self.current_sm,
                self.f,
                self.current_km,
            ]
            toWhitelist = [
                self.current_v,
                self.current_sm,
                self.f,
                self.current_km,
                newStakeManager,
            ]
            updateCanConsumeKeyNonce(self.current_km, currentWhitelist, toWhitelist)

            chain.sleep(st_sleep_time)

            # Generate claim to move all FLIP to new stakeManager
            stakeAmount = MIN_STAKE
            expiryTime = getChainTime() + (CLAIM_DELAY * 10)
            claimAmount = self.totalFlipstaked
            # Register Claim to transfer all flip
            callDataNoSig = self.current_sm.registerClaim.encode_input(
                agg_null_sig(self.current_km.address, chain.id),
                JUNK_HEX,
                claimAmount,
                newStakeManager,
                expiryTime,
            )
            tx = self.current_sm.registerClaim(
                AGG_SIGNER_1.getSigData(callDataNoSig, self.current_km.address),
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
                    self.current_sm.executeClaim(JUNK_HEX)

            chain.sleep(CLAIM_DELAY * 2)

            print("                   rule_executeClaim", newStakeManager.address)
            assert self.f.balanceOf(newStakeManager) == 0
            assert self.f.balanceOf(self.current_sm) == self.totalFlipstaked

            self.current_sm.executeClaim(JUNK_HEX, {"from": st_sender})

            assert self.f.balanceOf(newStakeManager) == self.totalFlipstaked
            assert self.f.balanceOf(self.current_sm) == 0

            # Dewhitelist old StakeManager
            currentWhitelist = [
                self.current_v,
                self.current_sm,
                self.f,
                self.current_km,
                newStakeManager,
            ]
            toWhitelist = [self.current_v, newStakeManager, self.f, self.current_km]
            updateCanConsumeKeyNonce(self.current_km, currentWhitelist, toWhitelist)

            self.current_sm = newStakeManager

        # Check that all the funds (ETH and FLIP) total amounts have not changed and have been transferred
        def invariant_bals(self):
            self.numTxsTested += 1
            assert self.current_v.balance() == self.TOTAL_FUNDS
            assert self.f.balanceOf(self.current_sm) == self.totalFlipstaked

        # KeyManager might have changed but references must be updated
        # FLIP contract should have remained the same
        def invariant_state_vars(self):
            assert self.current_v.getKeyManager() == self.current_km.address
            assert self.current_sm.getKeyManager() == self.current_km.address
            assert self.f.getKeyManager() == self.current_km.address

            assert self.current_sm.getFLIP() == self.f.address
            assert self.f.getLastSupplyUpdateBlockNumber() == self.lastSupplyBlockNumber

        def invariant_keyManager_whitelist(self):
            aggKeyNonceConsumers = [
                self.current_km,
                self.current_v,
                self.f,
                self.current_sm,
            ]
            assert self.current_km.getNumberWhitelistedAddresses() == len(
                aggKeyNonceConsumers
            )

            for aggKeyNonceConsumer in aggKeyNonceConsumers:
                assert (
                    self.current_km.canConsumeKeyNonce(aggKeyNonceConsumer.address)
                    == True
                )

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
