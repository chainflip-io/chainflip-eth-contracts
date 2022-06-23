from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy
from shared_tests import *
from utils import *
from random import choice

settings = {"stateful_step_count": 100, "max_examples": 50}


# Stateful test for all functions in the KeyManager
def test_keyManager(BaseStateMachine, state_machine, a, cfDeployAllWhitelist):

    # The total number of keys to have in the pool to assign and sign from
    TOTAL_KEYS = 4

    class StateMachine(BaseStateMachine):

        """
        This test calls functions from KeyManager in random orders. Keys are attempted to be set
        as random keys with a random signing key - all keys are from a pool of the default AGG_KEY
        and GOV_KEY plus freshly generated keys at the start of each run.
        The parameters used are so that they're small enough to increase the likelihood of the same
        address being used in multiple interactions and large enough to ensure there's variety in them
        """

        # Set up the initial test conditions once
        def __init__(cls, a, cfDeployAllWhitelist):
            # cls.aaa = {addr: addr for addr, addr in enumerate(a)}
            super().__init__(cls, a, cfDeployAllWhitelist)

        # Reset the local versions of state to compare the contract to after every run
        def setup(self):
            self.lastValidateTime = self.km.tx.timestamp
            self.keyIDToCurKeys = {AGG: AGG_SIGNER_1}
            self.allKeys = [*self.keyIDToCurKeys.values()] + (
                [Signer.gen_signer(None, {})]
                * (TOTAL_KEYS - len(self.keyIDToCurKeys.values()))
            )
            self.numTxsTested = 0
            self.governor = cfDeployAllWhitelist.gov
            self.communityKey = cfDeployAllWhitelist.communityKey
            self.currentWhitelist = cfDeployAllWhitelist.whitelisted
            self.ethBalskm = 0

        # Variables that will be a random value with each fcn/rule called

        st_sender = strategy("address")
        st_addrs = strategy("address[]")
        st_sig_key_idx = strategy("uint", max_value=TOTAL_KEYS - 1)
        st_new_key_idx = strategy("uint", max_value=TOTAL_KEYS - 1)
        st_msg_data = strategy("bytes")
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)
        st_amount = strategy("uint", max_value=TEST_AMNT)
        st_message = strategy("bytes32")

        # Updates the list of addresses that are nonce consumers
        def rule_updateCanConsumeKeyNonce(self, st_sender, st_addrs):
            # st_addrs will never be equal to whitelist (since whitelist contains contract addresses)
            currentWhitelist = choice([st_addrs, self.currentWhitelist])
            # st_addr will never contain self.km so add a chance for it to have it.
            newWhitelist = choice(
                [
                    st_addrs,
                    st_addrs + [self.km],
                    self.currentWhitelist,
                ]
            )

            currentWhitelistUnique = len(set(currentWhitelist)) == len(currentWhitelist)
            newWhitelistUnique = len(set(newWhitelist)) == len(newWhitelist)

            args = (currentWhitelist, newWhitelist)

            if len(currentWhitelist) != self.km.getNumberWhitelistedAddresses():
                print("        REV_MSG_LENGTH rule_updateCanConsumeKeyNonce")
                with reverts(REV_MSG_LENGTH):
                    signed_call_km(
                        self.km,
                        self.km.updateCanConsumeKeyNonce,
                        *args,
                        sender=st_sender,
                        signer=self.keyIDToCurKeys[AGG],
                    )
            else:
                # Check current whitelist
                for address in currentWhitelist:
                    if not self.km.canConsumeKeyNonce(address):
                        print(
                            "        REV_MSG_CANNOT_DEWHITELIST rule_updateCanConsumeKeyNonce"
                        )
                        with reverts(REV_MSG_CANNOT_DEWHITELIST):
                            signed_call_km(
                                self.km,
                                self.km.updateCanConsumeKeyNonce,
                                *args,
                                sender=st_sender,
                                signer=self.keyIDToCurKeys[AGG],
                            )
                        return
                if not currentWhitelistUnique:
                    print(
                        "        REV_MSG_CANNOT_DEWHITELIST rule_updateCanConsumeKeyNonce"
                    )
                    with reverts(REV_MSG_CANNOT_DEWHITELIST):
                        signed_call_km(
                            self.km,
                            self.km.updateCanConsumeKeyNonce,
                            *args,
                            sender=st_sender,
                            signer=self.keyIDToCurKeys[AGG],
                        )
                # Check new whitelist
                elif not newWhitelistUnique:
                    print("        REV_MSG_DUPLICATE rule_updateCanConsumeKeyNonce")
                    with reverts(REV_MSG_DUPLICATE):
                        signed_call_km(
                            self.km,
                            self.km.updateCanConsumeKeyNonce,
                            *args,
                            sender=st_sender,
                            signer=self.keyIDToCurKeys[AGG],
                        )
                else:
                    if not self.km in newWhitelist:
                        print(
                            "        REV_MSG_KEYMANAGER_WHITELIST rule_updateCanConsumeKeyNonce"
                        )
                        with reverts(REV_MSG_KEYMANAGER_WHITELIST):
                            signed_call_km(
                                self.km,
                                self.km.updateCanConsumeKeyNonce,
                                *args,
                                sender=st_sender,
                                signer=self.keyIDToCurKeys[AGG],
                            )
                    else:
                        print("                    rule_updateCanConsumeKeyNonce")
                        tx = signed_call_km(
                            self.km,
                            self.km.updateCanConsumeKeyNonce,
                            *args,
                            sender=st_sender,
                            signer=self.keyIDToCurKeys[AGG],
                        )
                        self.currentWhitelist = newWhitelist
                        self.lastValidateTime = tx.timestamp

        # Checks if consumeKeyNonce returns the correct value when called with a random sender,
        # signing key, random keyID that the signing key is supposed to be, and random msgData
        def rule_consumeKeyNonce(self, st_sender, st_sig_key_idx, st_msg_data):
            sigData = self.allKeys[st_sig_key_idx].getSigDataWithNonces(
                st_msg_data.hex(), nonces, self.km.address
            )
            toLog = (st_sender, st_sig_key_idx, st_msg_data)
            if not st_sender in self.currentWhitelist:
                with reverts(REV_MSG_WHITELIST):
                    tx = self.km.consumeKeyNonce(
                        sigData, cleanHexStr(sigData[2]), {"from": st_sender}
                    )
            elif self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[AGG]:
                print("                    rule_consumeKeyNonce", *toLog)
                if not st_sender in self.currentWhitelist:
                    with reverts(REV_MSG_WHITELIST):
                        tx = self.km.consumeKeyNonce(
                            sigData, cleanHexStr(sigData[2]), {"from": st_sender}
                        )
                else:
                    tx = self.km.consumeKeyNonce(
                        sigData, cleanHexStr(sigData[2]), {"from": st_sender}
                    )
                    self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print("        REV_MSG_SIG rule_consumeKeyNonce", *toLog)

                    self.km.consumeKeyNonce(
                        sigData, cleanHexStr(sigData[2]), {"from": st_sender}
                    )

        # Call setAggKeyWithAggKey with a random new key, signing key, and sender
        def rule_setAggKeyWithAggKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            toLog = (st_sender, st_sig_key_idx, st_new_key_idx)
            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[AGG]:
                print(f"                    {self.km.setAggKeyWithAggKey}", *toLog)
                tx = signed_call_km(
                    self.km,
                    self.km.setAggKeyWithAggKey,
                    self.allKeys[st_new_key_idx].getPubData(),
                    signer=self.allKeys[st_sig_key_idx],
                    sender=st_sender,
                )

                self.keyIDToCurKeys[AGG] = self.allKeys[st_new_key_idx]
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print(f"        REV_MSG_SIG {self.km.setAggKeyWithAggKey}", *toLog)
                    signed_call_km(
                        self.km,
                        self.km.setAggKeyWithAggKey,
                        self.allKeys[st_new_key_idx].getPubData(),
                        signer=self.allKeys[st_sig_key_idx],
                        sender=st_sender,
                    )

        # Call setGovKeyWithGovKey with a random new key - happens with low probability - 1/20
        def rule_setGovKeyWithGovKey(self, st_sender, st_addrs):
            newGovKey = choice(st_addrs)
            toLog = (st_sender, self.governor, newGovKey)
            if st_sender == self.governor:
                print(f"                    {self.km.setGovKeyWithGovKey}", *toLog)
                self.km.setGovKeyWithGovKey(newGovKey, {"from": st_sender})
                self.governor = newGovKey
            else:
                print(f"        REV_MSG_SIG {self.km.setGovKeyWithGovKey}", *toLog)
                with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
                    self.km.setGovKeyWithGovKey(newGovKey, {"from": st_sender})

        # Sleep for a random time so that setAggKeyWithGovKey can be called without reverting
        def rule_sleep(self, st_sleep_time):
            print("                    rule_sleep_2_days", st_sleep_time)
            chain.sleep(st_sleep_time)

        # Useful results are being impeded by most attempts at setAggKeyWithGovKey not having enough
        # delay - having 2 sleep methods makes it more common aswell as this which is enough of a delay
        # in itself, since Hypothesis usually picks small values as part of shrinking
        def rule_sleep_2_days(self):
            print("                    rule_sleep_2_days")
            chain.sleep(2 * DAY)

        # Call setAggKeyWithGovKey with a random new key, signing key, and sender
        def rule_setAggKeyWithGovKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            toLog = (st_sender, st_sig_key_idx, st_new_key_idx)
            if getChainTime() - self.lastValidateTime < AGG_KEY_TIMEOUT:
                print("        REV_MSG_DELAY rule_setAggKeyWithGovKey", *toLog)
                with reverts(REV_MSG_DELAY):
                    self.km.setAggKeyWithGovKey(
                        self.allKeys[st_new_key_idx].getPubData(),
                        {"from": self.governor},
                    )
            else:
                print("                    rule_setAggKeyWithGovKey", *toLog)
                self.km.setAggKeyWithGovKey(
                    self.allKeys[st_new_key_idx].getPubData(), {"from": self.governor}
                )

                self.keyIDToCurKeys[AGG] = self.allKeys[st_new_key_idx]

        # Updates community Key with a random new key - happens with low probability - 1/20
        def rule_setCommKeyWithCommKey(self, st_sender, st_addrs):
            newCommKey = choice(st_addrs)
            toLog = (st_sender, newCommKey, self.communityKey)
            if st_sender == self.communityKey:
                print("                    rule_setCommKeyWithCommKey", *toLog)
                self.km.setCommKeyWithCommKey(newCommKey, {"from": st_sender})
                self.communityKey = newCommKey
            else:
                print(
                    "        REV_MSG_KEYMANAGER_NOT_COMMUNITY _setCommKeyWithCommKey",
                    *toLog,
                )
                with reverts(REV_MSG_KEYMANAGER_NOT_COMMUNITY):
                    self.km.setCommKeyWithCommKey(newCommKey, {"from": st_sender})

        # Call setGovKeyWithAggKey with a random new key, signing key, and sender
        def rule_setGovKeyWithAggKey(
            self, st_sender, st_sig_key_idx, st_new_key_idx, st_addrs
        ):
            newGovKey = choice(st_addrs)
            toLog = (st_sender, st_sig_key_idx, st_new_key_idx)
            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[AGG]:
                print(f"                    {self.km.setGovKeyWithAggKey}", *toLog)
                tx = signed_call_km(
                    self.km,
                    self.km.setGovKeyWithAggKey,
                    newGovKey,
                    sender=st_sender,
                    signer=self.allKeys[st_sig_key_idx],
                )

                self.governor = newGovKey
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print(f"        REV_MSG_SIG {self.km.setGovKeyWithAggKey}", *toLog)
                    signed_call_km(
                        self.km,
                        self.km.setGovKeyWithAggKey,
                        newGovKey,
                        sender=st_sender,
                        signer=self.allKeys[st_sig_key_idx],
                    )

        # Call setCommKeyWithAggKey with a random new key, signing key, and sender
        def rule_setCommKeyWithAggKey(
            self, st_sender, st_sig_key_idx, st_new_key_idx, st_addrs
        ):
            newCommKey = choice(st_addrs)
            toLog = (st_sender, st_sig_key_idx, st_new_key_idx)
            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[AGG]:
                print(f"                    {self.km.setCommKeyWithAggKey}", *toLog)
                tx = signed_call_km(
                    self.km,
                    self.km.setCommKeyWithAggKey,
                    newCommKey,
                    sender=st_sender,
                    signer=self.allKeys[st_sig_key_idx],
                )

                self.communityKey = newCommKey
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print(f"        REV_MSG_SIG {self.km.setCommKeyWithAggKey}", *toLog)
                    signed_call_km(
                        self.km,
                        self.km.setCommKeyWithAggKey,
                        newCommKey,
                        sender=st_sender,
                        signer=self.allKeys[st_sig_key_idx],
                    )

        # Transfer ETH to the keyManager to check govWithdrawalEth
        def rule_transfer_eth(self, st_sender, st_amount):
            if st_sender.balance() >= st_amount:
                print("                    rule_transfer_eth", st_sender, st_amount)
                st_sender.transfer(self.km, st_amount)
                self.ethBalskm += st_amount

        # Governance attemps to withdraw any ETH - final balances will be check by the invariants
        def rule_govWithdrawalEth(self):
            iniEthBalsGov = self.governor.balance()
            print("                    rule_govWithdrawalEth")
            tx = self.km.govWithdrawEth({"from": self.governor})
            assert (
                iniEthBalsGov + self.ethBalskm
                == self.governor.balance() + calculateGasTransaction(tx)
            )
            self.ethBalskm = 0

        def rule_govAction(self, st_sender, st_message):
            if st_sender != self.governor:
                with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
                    self.km.govAction(JUNK_HEX, {"from": st_sender})
            print("                    rule_govAction")
            tx = self.km.govAction(st_message, {"from": self.governor})
            assert tx.events["GovernanceAction"]["message"] == "0x" + cleanHexStr(
                st_message
            )

        # Check lastValidateTime after every tx
        def invariant_lastValidateTime(self):
            self.numTxsTested += 1
            assert self.km.getLastValidateTime() == self.lastValidateTime

        def invariant_bals(self):
            assert self.ethBalskm == self.km.balance()

        def invariant_whitelist(self):
            assert self.km.getNumberWhitelistedAddresses() == len(self.currentWhitelist)
            for address in self.currentWhitelist:
                assert self.km.canConsumeKeyNonce(address) == True
            assert self.km.canConsumeKeyNonce(self.km) == True

        # Check the keys are correct after every tx
        def invariant_keys(self):
            assert (
                self.km.getAggregateKey() == self.keyIDToCurKeys[AGG].getPubDataWith0x()
            )

            assert (
                self.governor
                == self.km.getGovernanceKey()
                == self.sm.getGovernor()
                == self.v.getGovernor()
            )

            assert (
                self.communityKey
                == self.km.getCommunityKey()
                == self.sm.getCommunityKey()
                == self.v.getCommunityKey()
            )

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f"Total rules executed = {self.numTxsTested-1}")

    state_machine(StateMachine, a, cfDeployAllWhitelist, settings=settings)
