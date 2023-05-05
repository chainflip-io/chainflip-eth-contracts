from consts import *
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import strategy, contract_strategy
from utils import *
from hypothesis import strategies as hypStrat
from shared_tests import *
from deploy import deploy_new_stateChainGateway, deploy_new_vault, deploy_new_keyManager

settings = {"stateful_step_count": 100, "max_examples": 50}


# Stateful test for testing contract upgrades
def test_upgradability(
    BaseStateMachine,
    state_machine,
    a,
    cf,
    StateChainGateway,
    KeyManager,
    Vault,
    FLIP,
    DeployerStateChainGateway,
):
    class StateMachine(BaseStateMachine):

        # Max funds in the Vault
        TOTAL_FUNDS = 10**3 * E_18

        """
        This test deploys a new version of the following contracts: StateChainGateway, Vault and KeyManager

        All the references to these contracts need to be updated in the already deployed contracts.
        """

        # Set up the initial test conditions once
        def __init__(cls, a, cf):
            super().__init__(cls, a, cf)
            cls.totalFlipFunded = cf.flip.balanceOf(cf.stateChainGateway)

            # Store original contracts to be able to test upgradability
            cls.orig_scg = cls.scg
            cls.orig_v = cls.v
            cls.orig_km = cls.km

        # Reset the local versions of state to compare the contract to after every run
        def setup(self):
            # Set original contracts to be able to test upgradability
            self.scg = self.orig_scg
            self.v = self.orig_v
            self.km = self.orig_km

            self.lastValidateTime = self.deployerContract.tx.timestamp
            self.numTxsTested = 0

            # StateChainGateway
            self.lastSupplyBlockNumber = 0
            self.scg_communityKey = self.scg.getCommunityKey()
            self.scg_guard = self.scg.getCommunityGuardDisabled()
            self.scg_suspended = self.scg.getSuspendedState()

            # Vault - initialize with some funds
            a[3].transfer(self.v, self.TOTAL_FUNDS)
            self.v_communityKey = self.v.getCommunityKey()
            self.v_guard = self.v.getCommunityGuardDisabled()
            self.v_suspended = self.v.getSuspendedState()

        # Variables that will be a random value with each fcn/rule called

        st_sender = strategy("address")
        st_vault_transfer_amount = strategy("uint", max_value=TOTAL_FUNDS, exclude=0)
        st_sleep_time = strategy("uint", max_value=7 * DAY)

        # Deploys a new keyManager and updates all the references to it
        def rule_upgrade_keyManager(self, st_sender):
            aggKeyNonceConsumers = [self.scg, self.v]

            # Reusing current keyManager aggregateKey for simplicity
            newKeyManager = deploy_new_keyManager(
                st_sender,
                KeyManager,
                self.km.getAggregateKey(),
                st_sender,
                cf.communityKey,
            )

            print(
                "                    rule_upgrade_keyManager",
                st_sender,
                newKeyManager.address,
            )

            for aggKeyNonceConsumer in aggKeyNonceConsumers:
                assert aggKeyNonceConsumer.getKeyManager() == self.km
                # Gov key is different so omiting the check
                signed_call_km(
                    self.km,
                    aggKeyNonceConsumer.updateKeyManager,
                    newKeyManager,
                    True,
                    sender=st_sender,
                )

                assert aggKeyNonceConsumer.getKeyManager() == newKeyManager

            self.km = newKeyManager
            self.lastValidateTime = self.km.tx.timestamp

        # Deploys a new Vault and transfers the funds from the old Vault to the new one
        def rule_upgrade_Vault(
            self, st_sender, st_vault_transfer_amount, st_sleep_time
        ):
            newVault = deploy_new_vault(st_sender, Vault, KeyManager, self.km)

            # Vault can now validate and fetch but it has zero balance so it can't transfer
            args = [
                [
                    NATIVE_ADDR,
                    st_sender,
                    st_vault_transfer_amount,
                ]
            ]
            tx = signed_call_km(self.km, newVault.transfer, *args, sender=st_sender)

            # Transfer from oldVault to new Vault - unclear if we want to transfer all the balance
            startBalVault = self.v.balance()
            assert startBalVault >= st_vault_transfer_amount
            startBalRecipient = newVault.balance()

            args = [
                [
                    NATIVE_ADDR,
                    newVault,
                    st_vault_transfer_amount,
                ]
            ]
            signed_call_km(self.km, self.v.transfer, *args, sender=st_sender)

            assert self.v.balance() - startBalVault == -st_vault_transfer_amount
            assert newVault.balance() - startBalRecipient == st_vault_transfer_amount

            chain.sleep(st_sleep_time)

            # Transfer all the remaining funds to the new Vault
            startBalVault = self.v.balance()
            startBalRecipient = newVault.balance()

            if st_vault_transfer_amount > self.v.balance():
                print(
                    "        TRANSF_FAIL rule_upgrade_vault",
                    st_sender,
                    st_vault_transfer_amount,
                )
                tx = signed_call_km(self.km, self.v.transfer, *args, sender=st_sender)
                assert tx.events["TransferNativeFailed"][0].values() == [
                    newVault.address,
                    st_vault_transfer_amount,
                ]
            print(
                "                    rule_upgrade_vault",
                st_sender,
                st_vault_transfer_amount,
            )
            # Transfer all the remainding balance
            amountToTransfer = self.v.balance()
            args = [
                [
                    NATIVE_ADDR,
                    newVault,
                    amountToTransfer,
                ]
            ]
            signed_call_km(self.km, self.v.transfer, *args, sender=st_sender)

            assert self.v.balance() - startBalVault == -amountToTransfer
            assert newVault.balance() - startBalRecipient == amountToTransfer
            assert newVault.balance() == self.TOTAL_FUNDS

            self.v = newVault
            self.lastValidateTime = tx.timestamp
            self.v_communityKey = self.v_communityKey
            self.v_guard = False
            self.v_suspended = False

        # Deploys a new State Chain Gateway and transfers the FLIP tokens from the old SM to the new one
        def rule_upgrade_stateChainGateway(self, st_sender, st_sleep_time):
            (_, newStateChainGateway) = deploy_new_stateChainGateway(
                st_sender,
                KeyManager,
                StateChainGateway,
                FLIP,
                DeployerStateChainGateway,
                self.km.address,
                self.f.address,
                MIN_FUNDING,
            )

            chain.sleep(st_sleep_time)

            # Generate redemption to move all FLIP to new stateChainGateway
            expiryTime = getChainTime() + (REDEMPTION_DELAY * 10)
            redemptionAmount = self.totalFlipFunded
            # Register Redemption to transfer all flip
            args = (
                JUNK_HEX,
                redemptionAmount,
                newStateChainGateway,
                expiryTime,
            )
            signed_call_km(
                self.km, self.scg.registerRedemption, *args, sender=st_sender
            )

            chain.sleep(st_sleep_time)
            if st_sleep_time < REDEMPTION_DELAY:
                with reverts(REV_MSG_NOT_ON_TIME):
                    print(
                        "        REV_MSG_SIG rule_upgrade_stateChainGateway",
                        st_sleep_time,
                    )
                    self.scg.executeRedemption(JUNK_HEX, {"from": st_sender})

            chain.sleep(REDEMPTION_DELAY * 2)

            print(
                "                   rule_executeRedemption",
                newStateChainGateway.address,
            )
            assert self.f.balanceOf(newStateChainGateway) == 0
            assert self.f.balanceOf(self.scg) == self.totalFlipFunded

            self.scg.executeRedemption(JUNK_HEX, {"from": st_sender})

            assert self.f.balanceOf(newStateChainGateway) == self.totalFlipFunded
            assert self.f.balanceOf(self.scg) == 0

            assert self.f.issuer() == self.scg

            signed_call_km(
                self.km,
                self.scg.updateFlipIssuer,
                newStateChainGateway.address,
                False,
                sender=st_sender,
            )

            self.scg = newStateChainGateway
            self.scg_communityKey = self.scg_communityKey
            self.scg_guard = False
            self.scg_suspended = False
            assert self.f.issuer() == self.scg

        # Check that all the funds (NATIVE and FLIP) total amounts have not changed and have been transferred
        def invariant_bals(self):
            self.numTxsTested += 1
            assert self.v.balance() == self.TOTAL_FUNDS
            assert self.f.balanceOf(self.scg) == self.totalFlipFunded

        # KeyManager might have changed but references must be updated
        # FLIP contract should have remained the same
        def invariant_addresses(self):
            assert self.km.address == self.v.getKeyManager() == self.scg.getKeyManager()

            assert self.scg.getFLIP() == self.f.address

        # Check the state variables after every tx
        def invariant_state_vars(self):
            assert self.v_communityKey == self.v.getCommunityKey()
            assert self.v_guard == self.v.getCommunityGuardDisabled()
            assert self.v_suspended == self.v.getSuspendedState()
            assert self.scg_communityKey == self.scg.getCommunityKey()
            assert self.scg_guard == self.scg.getCommunityGuardDisabled()
            assert self.scg_suspended == self.scg.getSuspendedState()
            assert (
                self.scg.getLastSupplyUpdateBlockNumber() == self.lastSupplyBlockNumber
            )

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f"Total rules executed = {self.numTxsTested-1}")

    state_machine(
        StateMachine,
        a,
        cf,
        settings=settings,
    )
