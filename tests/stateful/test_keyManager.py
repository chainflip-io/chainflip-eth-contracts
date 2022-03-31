from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy
from utils import *
import random

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

        # Variables that will be a random value with each fcn/rule called

        st_sender = strategy("address")
        st_sig_key_idx = strategy("uint", max_value=TOTAL_KEYS - 1)
        st_new_key_idx = strategy("uint", max_value=TOTAL_KEYS - 1)
        # KEYID_TO_NUM - 2 to only take AGG
        st_keyID_num = strategy("uint", max_value=len(KEYID_TO_NUM) - 2)
        st_msg_data = strategy("bytes")
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)

        # Checks if consumeKeyNonce returns the correct value when called with a random sender,
        # signing key, random keyID that the signing key is supposed to be, and random msgData
        def rule_isValidSig(self, st_sender, st_sig_key_idx, st_keyID_num, st_msg_data):
            sigData = self.allKeys[st_sig_key_idx].getSigDataWithNonces(
                st_msg_data.hex(), nonces, NUM_TO_KEYID[st_keyID_num], self.km.address
            )
            if (
                self.allKeys[st_sig_key_idx]
                == self.keyIDToCurKeys[NUM_TO_KEYID[st_keyID_num]]
            ):
                print(
                    "                    rule_isValidSig",
                    st_sender,
                    st_sig_key_idx,
                    st_keyID_num,
                    st_msg_data,
                )
                tx = self.km.consumeKeyNonce(
                    sigData, cleanHexStr(sigData[2]), {"from": st_sender}
                )
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print(
                        "        REV_MSG_SIG rule_isValidSig",
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
            current_governor = random.choice([st_sender, self.governor])

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

        # Check the keys are correct after every tx
        def invariant_keys(self):
            assert (
                self.km.getAggregateKey() == self.keyIDToCurKeys[AGG].getPubDataWith0x()
            )
            assert self.km.getGovernanceKey() == self.governor

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f"Total rules executed = {self.numTxsTested-1}")

    state_machine(StateMachine, a, cfDeployAllWhitelist, settings=settings)
