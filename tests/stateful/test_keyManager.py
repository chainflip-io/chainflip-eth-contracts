from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy
from shared_tests import *
from utils import *
from random import choice
import time

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
            self.keyIDToCurKeys = {AGG: AGG_SIGNER_1, GOV: GOV_SIGNER_1}
            self.allKeys = [*self.keyIDToCurKeys.values()] + (
                [Signer.gen_signer(None, {})] * (TOTAL_KEYS - 2)
            )
            self.numTxsTested = 0
            self.governor = cfDeployAllWhitelist.gov
            self.currentWhitelist = cfDeployAllWhitelist.whitelisted

        # Variables that will be a random value with each fcn/rule called

        st_sender = strategy("address")
        st_addrs = strategy("address[]")
        st_sig_key_idx = strategy("uint", max_value=TOTAL_KEYS - 1)
        st_new_key_idx = strategy("uint", max_value=TOTAL_KEYS - 1)
        # KEYID_TO_NUM - 2 to only take AGG
        st_keyID_num = strategy("uint", max_value=len(KEYID_TO_NUM) - 2)
        st_msg_data = strategy("bytes")
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)

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

            if len(currentWhitelist) != self.km.getNumberWhitelistedAddresses():
                print(
                    "        REV_MSG_LENGTH rule_updateCanConsumeKeyNonce",
                    st_sender,
                    currentWhitelist,
                    newWhitelist,
                )
                with reverts(REV_MSG_LENGTH):
                    self._updateCanConsumeKeyNonce_sigNonce(
                        currentWhitelist, newWhitelist, st_sender
                    )
            else:
                # Check current whitelist
                for address in currentWhitelist:
                    if not self.km.canConsumeKeyNonce(address):
                        print(
                            "        REV_MSG_CANNOT_DEWHITELIST rule_updateCanConsumeKeyNonce",
                            st_sender,
                            currentWhitelist,
                            newWhitelist,
                        )
                        with reverts(REV_MSG_CANNOT_DEWHITELIST):
                            self._updateCanConsumeKeyNonce_sigNonce(
                                currentWhitelist, newWhitelist, st_sender
                            )
                        return
                if not currentWhitelistUnique:
                    print(
                        "        REV_MSG_CANNOT_DEWHITELIST rule_updateCanConsumeKeyNonce",
                        st_sender,
                        currentWhitelist,
                        newWhitelist,
                    )
                    with reverts(REV_MSG_CANNOT_DEWHITELIST):
                        self._updateCanConsumeKeyNonce_sigNonce(
                            currentWhitelist, newWhitelist, st_sender
                        )
                    return
                # Check new whitelist
                if not newWhitelistUnique:
                    print(
                        "        REV_MSG_DUPLICATE rule_updateCanConsumeKeyNonce",
                        st_sender,
                        currentWhitelist,
                        newWhitelist,
                    )
                    with reverts(REV_MSG_DUPLICATE):
                        self._updateCanConsumeKeyNonce_sigNonce(
                            currentWhitelist, newWhitelist, st_sender
                        )
                else:
                    if not self.km in newWhitelist:
                        print(
                            "        REV_MSG_KEYMANAGER_WHITELIST rule_updateCanConsumeKeyNonce",
                            st_sender,
                            currentWhitelist,
                            newWhitelist,
                        )
                        with reverts(REV_MSG_KEYMANAGER_WHITELIST):
                            self._updateCanConsumeKeyNonce_sigNonce(
                                currentWhitelist, newWhitelist, st_sender
                            )
                    else:
                        print(
                            "                    rule_updateCanConsumeKeyNonce",
                            st_sender,
                            currentWhitelist,
                            newWhitelist,
                        )
                        tx = self._updateCanConsumeKeyNonce_sigNonce(
                            currentWhitelist, newWhitelist, st_sender
                        )
                        self.currentWhitelist = newWhitelist
                        self.lastValidateTime = tx.timestamp

        def _updateCanConsumeKeyNonce_sigNonce(
            self, currentWhitelist, newWhitelist, st_sender
        ):
            callDataNoSig = self.km.updateCanConsumeKeyNonce.encode_input(
                agg_null_sig(self.km.address, chain.id), currentWhitelist, newWhitelist
            )
            return self.km.updateCanConsumeKeyNonce(
                self.keyIDToCurKeys[AGG].getSigDataWithNonces(
                    callDataNoSig, nonces, AGG, self.km.address
                ),
                currentWhitelist,
                newWhitelist,
                {"from": st_sender},
            )

        # Checks if consumeKeyNonce returns the correct value when called with a random sender,
        # signing key, random keyID that the signing key is supposed to be, and random msgData
        def rule_consumeKeyNonce(
            self, st_sender, st_sig_key_idx, st_keyID_num, st_msg_data
        ):
            sigData = self.allKeys[st_sig_key_idx].getSigDataWithNonces(
                st_msg_data.hex(), nonces, NUM_TO_KEYID[st_keyID_num], self.km.address
            )

            if not st_sender in self.currentWhitelist:
                with reverts(REV_MSG_WHITELIST):
                    tx = self.km.consumeKeyNonce(
                        sigData, cleanHexStr(sigData[2]), {"from": st_sender}
                    )
            elif (
                self.allKeys[st_sig_key_idx]
                == self.keyIDToCurKeys[NUM_TO_KEYID[st_keyID_num]]
            ):
                print(
                    "                    rule_consumeKeyNonce",
                    st_sender,
                    st_sig_key_idx,
                    st_keyID_num,
                    st_msg_data,
                )
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
                    print(
                        "        REV_MSG_SIG rule_consumeKeyNonce",
                        st_sender,
                        st_sig_key_idx,
                        st_keyID_num,
                        st_msg_data,
                    )

                    self.km.consumeKeyNonce(
                        sigData, cleanHexStr(sigData[2]), {"from": st_sender}
                    )

        # Replace a key with a random key - setAggKeyWithAggKey
        def _set_same_key_agg(
            self, st_sender, fcn, keyID, st_sig_key_idx, st_new_key_idx
        ):
            callDataNoSig = fcn.encode_input(
                agg_null_sig(self.km.address, chain.id),
                self.allKeys[st_new_key_idx].getPubData(),
            )
            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[keyID]:
                print(
                    f"                    {fcn}",
                    st_sender,
                    keyID,
                    st_sig_key_idx,
                    st_new_key_idx,
                )
                tx = fcn(
                    self.allKeys[st_sig_key_idx].getSigDataWithNonces(
                        callDataNoSig, nonces, AGG, self.km.address
                    ),
                    self.allKeys[st_new_key_idx].getPubData(),
                    {"from": st_sender},
                )

                self.keyIDToCurKeys[keyID] = self.allKeys[st_new_key_idx]
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print(
                        f"        REV_MSG_SIG {fcn}",
                        st_sender,
                        keyID,
                        st_sig_key_idx,
                        st_new_key_idx,
                    )
                    fcn(
                        self.allKeys[st_sig_key_idx].getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        self.allKeys[st_new_key_idx].getPubData(),
                        {"from": st_sender},
                    )

        # Replace the gov key (address) with a random gov address - setGovKeyWithGovKey
        def _set_same_key_gov(self, st_sender, fcn):
            current_governor = choice([st_sender, self.governor])

            if current_governor == self.governor:
                print(f"                    {fcn}", st_sender, self.governor)
                tx = fcn(st_sender, {"from": current_governor})
                self.governor = st_sender
            else:
                with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
                    fcn(st_sender, {"from": current_governor})

        # Call setAggKeyWithAggKey with a random new key, signing key, and sender
        def rule_setAggKeyWithAggKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            self._set_same_key_agg(
                st_sender,
                self.km.setAggKeyWithAggKey,
                AGG,
                st_sig_key_idx,
                st_new_key_idx,
            )

        # Call setAggKeyWithAggKey with a random new key, signing key, and sender
        def rule_setGovKeyWithGovKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            self._set_same_key_gov(st_sender, self.km.setGovKeyWithGovKey)

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
            if getChainTime() - self.lastValidateTime < AGG_KEY_TIMEOUT:
                print(
                    "        REV_MSG_DELAY rule_setAggKeyWithGovKey",
                    st_sender,
                    st_sig_key_idx,
                    st_new_key_idx,
                )
                with reverts(REV_MSG_DELAY):
                    self.km.setAggKeyWithGovKey(
                        self.allKeys[st_new_key_idx].getPubData(),
                        {"from": self.governor},
                    )
            else:
                print(
                    "                    rule_setAggKeyWithGovKey",
                    st_sender,
                    st_sig_key_idx,
                    st_new_key_idx,
                )
                tx = self.km.setAggKeyWithGovKey(
                    self.allKeys[st_new_key_idx].getPubData(), {"from": self.governor}
                )

                self.keyIDToCurKeys[AGG] = self.allKeys[st_new_key_idx]

        # Check lastValidateTime after every tx
        def invariant_lastValidateTime(self):
            self.numTxsTested += 1
            assert self.km.getLastValidateTime() == self.lastValidateTime

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
            assert self.km.getGovernanceKey() == self.governor

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f"Total rules executed = {self.numTxsTested-1}")
            # Add time.sleep due to brownie bug that kills virtual machine too quick
            time.sleep(5)

    state_machine(StateMachine, a, cfDeployAllWhitelist, settings=settings)
