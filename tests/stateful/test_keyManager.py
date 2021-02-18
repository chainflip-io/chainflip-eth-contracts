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

        # st_eth_amount = strategy("uint", max_value=MAX_ETH_SEND)
        # st_token_amount = strategy("uint", max_value=MAX_TOKEN_SEND)
        # st_swapID = strategy("uint", min_value=1, max_value=MAX_SWAPID)
        # # Only want the 1st 5 addresses so that the chances of multiple
        # # txs occurring from the same address is greatly increased while still
        # # ensuring diversity in senders
        # st_sender = strategy("address", length=MAX_NUM_SENDERS)
        # st_recip = strategy("address", length=MAX_NUM_SENDERS)
        # # st_recip = strategy("address")

        st_sender = strategy("address")
        st_sig_key_idx = strategy("uint", max_value=TOTAL_KEYS-1)
        st_new_key_idx = strategy("uint", max_value=TOTAL_KEYS-1)
        st_keyID_num = strategy("uint", max_value=len(KEYID_TO_NUM)-1)
        st_msg_data = strategy("bytes")


        def rule_isValidSig(self, st_sender, st_sig_key_idx, st_keyID_num, st_msg_data):
            sigData = self.allKeys[st_sig_key_idx].getSigData(st_msg_data.hex())

            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[NUM_TO_KEYID[st_keyID_num]]:
                tx = self.km.isValidSig(cleanHexStr(sigData[0]), sigData, st_keyID_num, {'from': st_sender})
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    self.km.isValidSig(cleanHexStr(sigData[0]), sigData, st_keyID_num, {'from': st_sender})
        

        def _set_same_key(self, st_sender, fcn, keyID, st_sig_key_idx, st_new_key_idx):
            callDataNoSig = fcn.encode_input(NULL_SIG_DATA, self.allKeys[st_new_key_idx].getPubData())
            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[keyID]:
                tx = fcn(self.allKeys[st_sig_key_idx].getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})

                self.keyIDToCurKeys[keyID] = self.allKeys[st_new_key_idx]
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    fcn(self.allKeys[st_sig_key_idx].getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})


        def rule_setAggKeyWithAggKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            self._set_same_key(st_sender, self.km.setAggKeyWithAggKey, AGG, st_sig_key_idx, st_new_key_idx)


        def rule_setGovKeyWithGovKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            self._set_same_key(st_sender, self.km.setGovKeyWithGovKey, GOV, st_sig_key_idx, st_new_key_idx)


        def rule_setAggKeyWithGovKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            callDataNoSig = self.km.setAggKeyWithGovKey.encode_input(NULL_SIG_DATA, self.allKeys[st_new_key_idx].getPubData())
            if chain.time() - self.lastValidateTime >= AGG_KEY_TIMEOUT:
                if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[GOV]:
                    tx = self.km.setAggKeyWithGovKey(self.allKeys[st_sig_key_idx].getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})

                    self.keyIDToCurKeys[GOV] = self.allKeys[st_new_key_idx]
                    self.lastValidateTime = tx.timestamp
                else:
                    with reverts(REV_MSG_SIG):
                        self.km.setAggKeyWithGovKey(self.allKeys[st_sig_key_idx].getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})
            else:
                with reverts(REV_MSG_DELAY):
                    self.km.setAggKeyWithGovKey(self.allKeys[st_sig_key_idx].getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})


        def invariant_lastValidateTime(self):
            assert self.km.getLastValidateTime() == self.lastValidateTime
        

        def invariant_keys(self):
            assert self.km.getAggregateKey() == self.keyIDToCurKeys[AGG].getPubDataWith0x()
            assert self.km.getGovernanceKey() == self.keyIDToCurKeys[GOV].getPubDataWith0x()

    
    settings = {"stateful_step_count": 500, "max_examples": 20}
    state_machine(StateMachine, a, cfDeploy, settings=settings)