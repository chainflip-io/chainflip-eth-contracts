from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy
from utils import *


def test_keyManager(BaseStateMachine, state_machine, a, cfDeploy):

    TOTAL_KEYS = 4
    
    class StateMachine(BaseStateMachine):

        def __init__(cls, a, cfDeploy):
            # cls.aaa = {addr: addr for addr, addr in enumerate(a)}
            super().__init__(cls, a, cfDeploy)


        def setup(self):
            self.lastValidateTime = self.km.tx.timestamp
            self.keyIDToCurKeys = {AGG: AGG_SIGNER_1, GOV: GOV_SIGNER_1}
            self.allKeys = [*self.keyIDToCurKeys.values()] + ([Signer.gen_signer()] * (TOTAL_KEYS - 2))
            self.numTxsTested = 0


        st_sender = strategy("address")
        st_sig_key_idx = strategy("uint", max_value=TOTAL_KEYS-1)
        st_new_key_idx = strategy("uint", max_value=TOTAL_KEYS-1)
        st_keyID_num = strategy("uint", max_value=len(KEYID_TO_NUM)-1)
        st_msg_data = strategy("bytes")
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)


        def rule_isValidSig(self, st_sender, st_sig_key_idx, st_keyID_num, st_msg_data):
            sigData = self.allKeys[st_sig_key_idx].getSigData(st_msg_data.hex())

            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[NUM_TO_KEYID[st_keyID_num]]:
                print('             rule_isValidSig', st_sender, st_sig_key_idx, st_keyID_num, st_msg_data)
                tx = self.km.isValidSig(cleanHexStr(sigData[0]), sigData, st_keyID_num, {'from': st_sender})
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print('REV_MSG_SIG rule_isValidSig', st_sender, st_sig_key_idx, st_keyID_num, st_msg_data)
                    self.km.isValidSig(cleanHexStr(sigData[0]), sigData, st_keyID_num, {'from': st_sender})

        

        def _set_same_key(self, st_sender, fcn, keyID, st_sig_key_idx, st_new_key_idx):
            callDataNoSig = fcn.encode_input(NULL_SIG_DATA, self.allKeys[st_new_key_idx].getPubData())
            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[keyID]:
                print(f'             {fcn}', st_sender, keyID, st_sig_key_idx, st_new_key_idx)
                tx = fcn(self.allKeys[st_sig_key_idx].getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})

                self.keyIDToCurKeys[keyID] = self.allKeys[st_new_key_idx]
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print(f'REV_MSG_SIG {fcn}', st_sender, keyID, st_sig_key_idx, st_new_key_idx)
                    fcn(self.allKeys[st_sig_key_idx].getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})


        def rule_setAggKeyWithAggKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            self._set_same_key(st_sender, self.km.setAggKeyWithAggKey, AGG, st_sig_key_idx, st_new_key_idx)


        def rule_setGovKeyWithGovKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            self._set_same_key(st_sender, self.km.setGovKeyWithGovKey, GOV, st_sig_key_idx, st_new_key_idx)
        

        def rule_sleep(self, st_sleep_time):
            chain.sleep(st_sleep_time)
        

        # Useful results are being impeded by most attempts at setAggKeyWithGovKey not having enough
        # delay - having 2 sleep methods makes it more common aswell as this which is enough of a delay
        # in itself, since Hypothesis usually picks small values as part of shrinking
        def rule_sleep_2_days(self):
            chain.sleep(2 * DAY)


        def rule_setAggKeyWithGovKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            callDataNoSig = self.km.setAggKeyWithGovKey.encode_input(NULL_SIG_DATA, self.allKeys[st_new_key_idx].getPubData())
            if chain.time() - self.lastValidateTime < AGG_KEY_TIMEOUT:
                print('REV_MSG_DELAY rule_setAggKeyWithGovKey', st_sender, st_sig_key_idx, st_new_key_idx)
                with reverts(REV_MSG_DELAY):
                    self.km.setAggKeyWithGovKey(self.allKeys[st_sig_key_idx].getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})
            elif self.allKeys[st_sig_key_idx] != self.keyIDToCurKeys[GOV]:
                print('REV_MSG_SIG rule_setAggKeyWithGovKey', st_sender, st_sig_key_idx, st_new_key_idx)
                with reverts(REV_MSG_SIG):
                    self.km.setAggKeyWithGovKey(self.allKeys[st_sig_key_idx].getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})
            else:
                print('             rule_setAggKeyWithGovKey', st_sender, st_sig_key_idx, st_new_key_idx)
                tx = self.km.setAggKeyWithGovKey(self.allKeys[st_sig_key_idx].getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})

                self.keyIDToCurKeys[AGG] = self.allKeys[st_new_key_idx]
                self.lastValidateTime = tx.timestamp


        def invariant_lastValidateTime(self):
            self.numTxsTested += 1
            assert self.km.getLastValidateTime() == self.lastValidateTime
        

        def invariant_keys(self):
            assert self.km.getAggregateKey() == self.keyIDToCurKeys[AGG].getPubDataWith0x()
            assert self.km.getGovernanceKey() == self.keyIDToCurKeys[GOV].getPubDataWith0x()
        

        def teardown(self):
            print(self.numTxsTested)

    
    settings = {"stateful_step_count": 500, "max_examples": 20}
    state_machine(StateMachine, a, cfDeploy, settings=settings)