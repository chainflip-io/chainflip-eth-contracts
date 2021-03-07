from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy
from utils import *
from hypothesis import strategies as hypStrat


def test_stakeManager(BaseStateMachine, state_machine, a, cfDeploy):

    NUM_STAKERS = 5
    INIT_STAKE = 10**25
    # Setting this low because Brownie/Hypothesis 'shrinks' random
    # numbers so that they cluster near the minimum, and we want to maximise
    # the amount of non-reverted txs there are, while also allowing for some reverts
    INIT_MIN_STAKE = 1000
    MAX_TEST_STAKE = 10**24
    
    class StateMachine(BaseStateMachine):

        def __init__(cls, a, cfDeploy):
            super().__init__(cls, a, cfDeploy)

            callDataNoSig = cls.sm.setMinStake.encode_input(NULL_SIG_DATA, INIT_MIN_STAKE)
            cls.sm.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), INIT_MIN_STAKE)

            cls.stakers = a[:NUM_STAKERS]

            for staker in cls.stakers:
                cls.f.transfer(staker, INIT_STAKE, {'from': a[0]})
                cls.f.approve(cls.sm, INIT_STAKE, {'from': staker})
            # Send excess from the deployer to the zero address so that all stakers start
            # with the same balance to make the accounting simpler
            cls.f.transfer("0x0000000000000000000000000000000000000001", cls.f.balanceOf(a[0]) - INIT_STAKE, {'from': a[0]})


        def setup(self):
            self.lastMintBlockNum = self.sm.tx.block_number
            self.emissionPerBlock = EMISSION_PER_BLOCK
            self.totalStake = 0
            self.minStake = INIT_MIN_STAKE
            self.allAddrs = self.stakers + [self.sm]
            
            # Eth bals shouldn't change in this test, but just to be sure...
            self.ethBals = {addr: INIT_ETH_BAL if addr in a else 0 for addr in self.allAddrs}
            self.flipBals = {addr: INIT_STAKE if addr in self.stakers else 0 for addr in self.allAddrs}
            self.numTxsTested = 0


        st_sender = strategy("address")
        st_staker = strategy("address", length=NUM_STAKERS)
        st_nodeID = strategy("uint")
        st_amount = strategy("uint", max_value=MAX_TEST_STAKE)
        # This would be 10x the initial supply in 1 year, so is a reasonable max without
        # uint overflowing
        st_emission = strategy("uint", max_value=370 * E_18)
        # In reality this high amount isn't really realistic, but for the sake of testing
        st_minStake = strategy("uint", max_value=int(INIT_STAKE/2))
        # So there's a 1% chance of a bad sig to maximise useful txs
        st_signer_agg = hypStrat.sampled_from(([AGG_SIGNER_1] * 99) + [GOV_SIGNER_1])
        st_signer_gov = hypStrat.sampled_from([AGG_SIGNER_1] + ([GOV_SIGNER_1] * 99))


        def rule_stake(self, st_staker, st_nodeID, st_amount):
            if st_nodeID == 0:
                print('rule_stake NODEID', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.stake(st_nodeID, st_amount, {'from': st_staker})
            elif st_amount < self.minStake:
            # st_amount = MAX_TEST_STAKE - st_amount
            # if st_amount < self.minStake:
                print('rule_stake MIN_STAKE', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_MIN_STAKE):
                    self.sm.stake(st_nodeID, st_amount, {'from': st_staker})
            elif st_amount > self.flipBals[st_staker]:
                print('rule_stake REV_MSG_EXCEED_BAL', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_EXCEED_BAL):
                    self.sm.stake(st_nodeID, st_amount, {'from': st_staker})
            else:
                print('             rule_stake ', st_staker, st_nodeID, st_amount/E_18)
                self.sm.stake(st_nodeID, st_amount, {'from': st_staker})

                self.flipBals[st_staker] -= st_amount
                self.flipBals[self.sm] += st_amount
                self.totalStake += st_amount
            

        def rule_claim(self, st_signer_agg, st_nodeID, st_staker, st_amount, st_sender):
            callDataNoSig = self.sm.claim.encode_input(NULL_SIG_DATA, st_nodeID, st_staker, st_amount)
            inflation = getInflation(self.lastMintBlockNum, web3.eth.blockNumber + 1, self.emissionPerBlock)

            if st_nodeID == 0:
                print('rule_claim NODEID', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.claim(st_signer_agg.getSigData(callDataNoSig), st_nodeID, st_staker, st_amount, {'from': st_sender})
            elif st_amount == 0:
                print('rule_claim AMOUNT', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.claim(st_signer_agg.getSigData(callDataNoSig), st_nodeID, st_staker, st_amount, {'from': st_sender})
            elif st_signer_agg != AGG_SIGNER_1:
                print('rule_claim REV_MSG_SIG', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_SIG):
                    self.sm.claim(st_signer_agg.getSigData(callDataNoSig), st_nodeID, st_staker, st_amount, {'from': st_sender})
            elif st_amount > self.flipBals[self.sm] + inflation:
                print('rule_claim REV_MSG_EXCEED_BAL', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_EXCEED_BAL):
                    self.sm.claim(st_signer_agg.getSigData(callDataNoSig), st_nodeID, st_staker, st_amount, {'from': st_sender})
            else:
                print('             rule_claim ', st_staker, st_nodeID, st_amount/E_18)
                tx = self.sm.claim(st_signer_agg.getSigData(callDataNoSig), st_nodeID, st_staker, st_amount, {'from': st_sender})

                self.flipBals[st_staker] += st_amount
                self.flipBals[self.sm] -= (st_amount - inflation)
                self.totalStake -= (st_amount - inflation)
                self.lastMintBlockNum = tx.block_number
        

        def rule_setEmissionPerBlock(self, st_emission, st_signer_gov, st_sender):
            callDataNoSig = self.sm.setEmissionPerBlock.encode_input(NULL_SIG_DATA, st_emission)

            if st_emission == 0:
                print('rule_setEmissionPerBlock REV_MSG_NZ_UINT', st_emission, st_signer_gov, st_sender)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.setEmissionPerBlock(st_signer_gov.getSigData(callDataNoSig), st_emission, {'from': st_sender})
            elif st_signer_gov != GOV_SIGNER_1:
                print('rule_setEmissionPerBlock REV_MSG_SIG', st_emission, st_signer_gov, st_sender)
                with reverts(REV_MSG_SIG):
                    self.sm.setEmissionPerBlock(st_signer_gov.getSigData(callDataNoSig), st_emission, {'from': st_sender})
            else:
                print('                     rule_setEmissionPerBlock', st_emission, st_signer_gov, st_sender)
                tx = self.sm.setEmissionPerBlock(st_signer_gov.getSigData(callDataNoSig), st_emission, {'from': st_sender})

                inflation = getInflation(self.lastMintBlockNum, web3.eth.blockNumber, self.emissionPerBlock)
                self.flipBals[self.sm] += inflation
                self.totalStake += inflation
                self.lastMintBlockNum = tx.block_number
                self.emissionPerBlock = st_emission


        def rule_setMinStake(self, st_minStake, st_signer_gov, st_sender):
            callDataNoSig = self.sm.setMinStake.encode_input(NULL_SIG_DATA, st_minStake)

            if st_minStake == 0:
                print('rule_setMinstake REV_MSG_NZ_UINT', st_minStake, st_signer_gov, st_sender)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.setMinStake(st_signer_gov.getSigData(callDataNoSig), st_minStake, {'from': st_sender})
            elif st_signer_gov != GOV_SIGNER_1:
                print('rule_setMinstake REV_MSG_SIG', st_minStake, st_signer_gov, st_sender)
                with reverts(REV_MSG_SIG):
                    self.sm.setMinStake(st_signer_gov.getSigData(callDataNoSig), st_minStake, {'from': st_sender})
            else:
                print('                     rule_setMinstake', st_minStake, st_signer_gov, st_sender)
                tx = self.sm.setMinStake(st_signer_gov.getSigData(callDataNoSig), st_minStake, {'from': st_sender})

                self.minStake = st_minStake


        # Variable(s) that shouldn't change since there's no intentional way to
        def invariant_nonchangeable(self):
            assert self.sm.getKeyManager() == self.km.address
            assert self.sm.getFLIPAddress() == self.f.address
        

        def invariant_state_vars(self):
            assert self.sm.getLastMintBlockNum() == self.lastMintBlockNum
            assert self.sm.getEmissionPerBlock() == self.emissionPerBlock
            assert self.sm.getMinimumStake() == self.minStake
        

        def invariant_bals(self):
            for addr in self.allAddrs:
                assert addr.balance() == self.ethBals[addr]
                assert self.f.balanceOf(addr) == self.flipBals[addr]
        

        def invariant_inflation_calcs(self):
            self.numTxsTested += 1
            # Test in present and future
            assert self.sm.getInflationInFuture(0) == getInflation(self.lastMintBlockNum, web3.eth.blockNumber, self.emissionPerBlock)
            assert self.sm.getInflationInFuture(100) == getInflation(self.lastMintBlockNum, web3.eth.blockNumber+100, self.emissionPerBlock)
            assert self.sm.getTotalStakeInFuture(0) == self.totalStake + getInflation(self.lastMintBlockNum, web3.eth.blockNumber, self.emissionPerBlock)
            assert self.sm.getTotalStakeInFuture(100) == self.totalStake + getInflation(self.lastMintBlockNum, web3.eth.blockNumber+100, self.emissionPerBlock)
        

        def teardown(self):
            print('Num rules used = ', self.numTxsTested)
            
    
    # settings = {"stateful_step_count": 50, "max_examples": 10, "phases": {"shrink":False}}
    settings = {"stateful_step_count": 1000, "max_examples": 50}
    state_machine(StateMachine, a, cfDeploy, settings=settings)