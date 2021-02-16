from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy


def test_keyManager(BaseStateMachine, state_machine, a, cfDeploy):

    TOTAL_KEYS = 5
    
    class StateMachine(BaseStateMachine):

        def __init__(cls, a, cfDeploy):
            # cls.aaa = {addr: addr for addr, addr in enumerate(a)}
            super().__init__(cls, a, cfDeploy)


        def setup(self):
            self.lastValidateTime = self.sm.tx.timestamp
            self.aggSigner = AGG_SIGNER_1
            self.govSigner = GOV_SIGNER_1
            self.keys = [self.aggSigner, self.govSigner] + ([Signer.gen_key()] * (TOTAL_KEYS - 2))

        # st_eth_amount = strategy("uint", max_value=MAX_ETH_SEND)
        # st_token_amount = strategy("uint", max_value=MAX_TOKEN_SEND)
        # st_swapID = strategy("uint", min_value=1, max_value=MAX_SWAPID)
        # # Only want the 1st 5 addresses so that the chances of multiple
        # # txs occurring from the same address is greatly increased while still
        # # ensuring diversity in senders
        # st_sender = strategy("address", length=MAX_NUM_SENDERS)
        # st_recip = strategy("address", length=MAX_NUM_SENDERS)
        # # st_recip = strategy("address")

        


    
    settings = {"stateful_step_count": 50, "max_examples": 20}
    state_machine(StateMachine, a, cfDeploy, settings=settings)