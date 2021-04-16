from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy
from utils import *
from hypothesis import strategies as hypStrat


settings = {"stateful_step_count": 100, "max_examples": 50}


# Stateful test for all functions in the StakeManager
def test_stakeManager(BaseStateMachine, state_machine, a, cfDeploy):

    NUM_STAKERS = 5
    INIT_STAKE = 10**25
    # Setting this low because Brownie/Hypothesis 'shrinks' random
    # numbers so that they cluster near the minimum, and we want to maximise
    # the amount of non-reverted txs there are, while also allowing for some reverts
    INIT_MIN_STAKE = 1000
    MAX_TEST_STAKE = 10**24
    
    class StateMachine(BaseStateMachine):

        """
        This test calls functions from StakeManager in random orders. There's a NUM_STAKERS number
        of stakers that randomly `stake` and are randomly the recipients of `claim`.
        The parameters used are so that they're small enough to increase the likelihood of the same
        address being used in multiple interactions (e.g. 2  x stakes then a claim etc) and large
        enough to ensure there's variety in them
        """

        # Set up the initial test conditions once
        def __init__(cls, a, cfDeploy):
            super().__init__(cls, a, cfDeploy)

            # Set the initial minStake to be different than the default in cfDeploy
            callDataNoSig = cls.sm.setMinStake.encode_input(NULL_SIG_DATA, INIT_MIN_STAKE)
            cls.sm.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), INIT_MIN_STAKE)

            cls.stakers = a[:NUM_STAKERS]

            for staker in cls.stakers:
                cls.f.transfer(staker, INIT_STAKE, {'from': a[0]})
                cls.f.approve(cls.sm, INIT_STAKE, {'from': staker})
            # Send excess from the deployer to the zero address so that all stakers start
            # with the same balance to make the accounting simpler
            cls.f.transfer("0x0000000000000000000000000000000000000001", cls.f.balanceOf(a[0]) - INIT_STAKE, {'from': a[0]})


        # Reset the local versions of state to compare the contract to after every run
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


        # Variables that will be a random value with each fcn/rule called

        st_sender = strategy("address")
        st_staker = strategy("address", length=NUM_STAKERS)
        st_receivers = strategy('address[]', length=NUM_STAKERS)
        st_nodeID = strategy("uint")
        st_nodeIDs = strategy('uint256[]')
        st_amount = strategy("uint", max_value=MAX_TEST_STAKE)
        st_amounts = strategy('uint256[]', max_value=MAX_TEST_STAKE)
        # This would be 10x the initial supply in 1 year, so is a reasonable max without
        # uint overflowing
        st_emission = strategy("uint", max_value=370 * E_18)
        # In reality this high amount isn't really realistic, but for the sake of testing
        st_minStake = strategy("uint", max_value=int(INIT_STAKE/2))
        # So there's a 1% chance of a bad sig to maximise useful txs
        st_signer_agg = hypStrat.sampled_from(([AGG_SIGNER_1] * 99) + [GOV_SIGNER_1])
        st_signer_gov = hypStrat.sampled_from([AGG_SIGNER_1] + ([GOV_SIGNER_1] * 99))


        # Stakes a random amount from a random staker to a random nodeID
        def rule_stake(self, st_staker, st_nodeID, st_amount):
            if st_nodeID == 0:
                print('        NODEID rule_stake', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.stake(st_nodeID, st_amount, {'from': st_staker})
            elif st_amount < self.minStake:
            # st_amount = MAX_TEST_STAKE - st_amount
            # if st_amount < self.minStake:
                print('        MIN_STAKE rule_stake', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_MIN_STAKE):
                    self.sm.stake(st_nodeID, st_amount, {'from': st_staker})
            elif st_amount > self.flipBals[st_staker]:
                print('        REV_MSG_EXCEED_BAL rule_stake', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_EXCEED_BAL):
                    self.sm.stake(st_nodeID, st_amount, {'from': st_staker})
            else:
                print('                    rule_stake', st_staker, st_nodeID, st_amount/E_18)
                self.sm.stake(st_nodeID, st_amount, {'from': st_staker})

                self.flipBals[st_staker] -= st_amount
                self.flipBals[self.sm] += st_amount
                self.totalStake += st_amount
            

        # Claims a random amount from a random nodeID to a random recipient
        def rule_claim(self, st_signer_agg, st_nodeID, st_staker, st_amount, st_sender):
            callDataNoSig = self.sm.claim.encode_input(NULL_SIG_DATA, st_nodeID, st_staker, st_amount)
            inflation = getInflation(self.lastMintBlockNum, web3.eth.blockNumber + 1, self.emissionPerBlock)

            if st_nodeID == 0:
                print('        NODEID rule_claim', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.claim(st_signer_agg.getSigData(callDataNoSig), st_nodeID, st_staker, st_amount, {'from': st_sender})
            elif st_amount == 0:
                print('        AMOUNT rule_claim', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.claim(st_signer_agg.getSigData(callDataNoSig), st_nodeID, st_staker, st_amount, {'from': st_sender})
            elif st_signer_agg != AGG_SIGNER_1:
                print('        REV_MSG_SIG rule_claim', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_SIG):
                    self.sm.claim(st_signer_agg.getSigData(callDataNoSig), st_nodeID, st_staker, st_amount, {'from': st_sender})
            elif st_amount > self.flipBals[self.sm] + inflation:
                print('        REV_MSG_EXCEED_BAL rule_claim', st_staker, st_nodeID, st_amount/E_18)
                with reverts(REV_MSG_EXCEED_BAL):
                    self.sm.claim(st_signer_agg.getSigData(callDataNoSig), st_nodeID, st_staker, st_amount, {'from': st_sender})
            else:
                print('                    rule_claim ', st_staker, st_nodeID, st_amount/E_18)
                tx = self.sm.claim(st_signer_agg.getSigData(callDataNoSig), st_nodeID, st_staker, st_amount, {'from': st_sender})

                self.flipBals[st_staker] += st_amount
                self.flipBals[self.sm] -= (st_amount - inflation)
                self.totalStake -= (st_amount - inflation)
                self.lastMintBlockNum = tx.block_number
        
        
        # Claims a random amount from a random nodeID to a random recipient. Since there's no real way
        # to get the lengths of the input arrays to be the same most of the time, I'm going to have to
        # use a random number to determine whether or not to concat all arrays to the
        # length of the shortest so that we'll get mostly valid txs and maximise usefulness. The
        # easiest random num to use is the length of the arrays themselves - I'm gonna use '5' as the
        # magic shortest length that should trigger not concating for no particular reason
        def rule_claimBatch(self, st_signer_agg, st_nodeIDs, st_receivers, st_amounts, st_sender):
            callDataNoSig = self.sm.claimBatch.encode_input(NULL_SIG_DATA, st_nodeIDs, st_receivers, st_amounts)
            inflation = getInflation(self.lastMintBlockNum, web3.eth.blockNumber + 1, self.emissionPerBlock)
            minLen = min(map(len, [st_nodeIDs, st_receivers, st_amounts]))
            maxLen = max(map(len, [st_nodeIDs, st_receivers, st_amounts]))

            if st_signer_agg != AGG_SIGNER_1:
                print('        REV_MSG_SIG rule_claimBatch', st_signer_agg, st_nodeIDs, st_receivers, st_amounts, st_sender)
                with reverts(REV_MSG_SIG):
                    self.sm.claimBatch(st_signer_agg.getSigData(callDataNoSig), st_nodeIDs, st_receivers, st_amounts, {'from': st_sender})
            elif minLen == 5 and minLen != maxLen:
                print('        REV_MSG_SM_ARR_LEN rule_claimBatch', st_signer_agg, st_nodeIDs, st_receivers, st_amounts, st_sender)
                with reverts(REV_MSG_SM_ARR_LEN):
                    self.sm.claimBatch(st_signer_agg.getSigData(callDataNoSig), st_nodeIDs, st_receivers, st_amounts, {'from': st_sender})
            else:
                st_nodeIDs = st_nodeIDs[:minLen]
                st_receivers = st_receivers[:minLen]
                st_amounts = st_amounts[:minLen]
                minLen = trimToShortest([st_nodeIDs, st_receivers, st_amounts])
                
                callDataNoSig = self.sm.claimBatch.encode_input(NULL_SIG_DATA, st_nodeIDs, st_receivers, st_amounts)

                if sum(st_amounts) > self.flipBals[self.sm] + inflation:
                    print('        REV_MSG_EXCEED_BAL rule_claimBatch', st_signer_agg, st_nodeIDs, st_receivers, st_amounts, st_sender)
                    with reverts(REV_MSG_EXCEED_BAL):
                        self.sm.claimBatch(st_signer_agg.getSigData(callDataNoSig), st_nodeIDs, st_receivers, st_amounts, {'from': st_sender})
                else:
                    print('                    rule_claimBatch', st_signer_agg, st_nodeIDs, st_receivers, st_amounts, st_sender)
                    tx = self.sm.claimBatch(st_signer_agg.getSigData(callDataNoSig), st_nodeIDs, st_receivers, st_amounts, {'from': st_sender})

                    self.lastMintBlockNum = tx.block_number
                    self.totalStake -= (sum(st_amounts) - inflation)
                    self.flipBals[self.sm] -= (sum(st_amounts) - inflation)
                    for i in range(minLen):
                        self.flipBals[st_receivers[i]] += st_amounts[i]
                


        

        # Sets the emission rate as a random value, signs with a random (probability-weighted) sig,
        # and sends the tx from a random address
        def rule_setEmissionPerBlock(self, st_emission, st_signer_gov, st_sender):
            callDataNoSig = self.sm.setEmissionPerBlock.encode_input(NULL_SIG_DATA, st_emission)

            if st_emission == 0:
                print('        REV_MSG_NZ_UINT rule_setEmissionPerBlock', st_emission, st_signer_gov, st_sender)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.setEmissionPerBlock(st_signer_gov.getSigData(callDataNoSig), st_emission, {'from': st_sender})
            elif st_signer_gov != GOV_SIGNER_1:
                print('        REV_MSG_SIG rule_setEmissionPerBlock', st_emission, st_signer_gov, st_sender)
                with reverts(REV_MSG_SIG):
                    self.sm.setEmissionPerBlock(st_signer_gov.getSigData(callDataNoSig), st_emission, {'from': st_sender})
            else:
                print('                    rule_setEmissionPerBlock', st_emission, st_signer_gov, st_sender)
                tx = self.sm.setEmissionPerBlock(st_signer_gov.getSigData(callDataNoSig), st_emission, {'from': st_sender})

                inflation = getInflation(self.lastMintBlockNum, web3.eth.blockNumber, self.emissionPerBlock)
                self.flipBals[self.sm] += inflation
                self.totalStake += inflation
                self.lastMintBlockNum = tx.block_number
                self.emissionPerBlock = st_emission


        # Sets the minimum stake as a random value, signs with a random (probability-weighted) sig,
        # and sends the tx from a random address
        def rule_setMinStake(self, st_minStake, st_signer_gov, st_sender):
            callDataNoSig = self.sm.setMinStake.encode_input(NULL_SIG_DATA, st_minStake)

            if st_minStake == 0:
                print('        REV_MSG_NZ_UINT rule_setMinstake', st_minStake, st_signer_gov, st_sender)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.setMinStake(st_signer_gov.getSigData(callDataNoSig), st_minStake, {'from': st_sender})
            elif st_signer_gov != GOV_SIGNER_1:
                print('        REV_MSG_SIG rule_setMinstake', st_minStake, st_signer_gov, st_sender)
                with reverts(REV_MSG_SIG):
                    self.sm.setMinStake(st_signer_gov.getSigData(callDataNoSig), st_minStake, {'from': st_sender})
            else:
                print('                    rule_setMinstake', st_minStake, st_signer_gov, st_sender)
                tx = self.sm.setMinStake(st_signer_gov.getSigData(callDataNoSig), st_minStake, {'from': st_sender})

                self.minStake = st_minStake


        # Check variable(s) after every tx that shouldn't change since there's
        # no intentional way to
        def invariant_nonchangeable(self):
            assert self.sm.getKeyManager() == self.km.address
            assert self.sm.getFLIPAddress() == self.f.address
        

        # Check all the state variables that can be changed after every tx
        def invariant_state_vars(self):
            assert self.sm.getLastMintBlockNum() == self.lastMintBlockNum
            assert self.sm.getEmissionPerBlock() == self.emissionPerBlock
            assert self.sm.getMinimumStake() == self.minStake
        

        # Check all the balances of every address are as they should be after every tx
        def invariant_bals(self):
            for addr in self.allAddrs:
                assert addr.balance() == self.ethBals[addr]
                assert self.f.balanceOf(addr) == self.flipBals[addr]
        

        # Check all the balances of every address are as they should be after every tx
        def invariant_inflation_calcs(self):
            self.numTxsTested += 1
            # Test in present and future
            assert self.sm.getInflationInFuture(0) == getInflation(self.lastMintBlockNum, web3.eth.blockNumber, self.emissionPerBlock)
            assert self.sm.getInflationInFuture(100) == getInflation(self.lastMintBlockNum, web3.eth.blockNumber+100, self.emissionPerBlock)
            assert self.sm.getTotalStakeInFuture(0) == self.totalStake + getInflation(self.lastMintBlockNum, web3.eth.blockNumber, self.emissionPerBlock)
            assert self.sm.getTotalStakeInFuture(100) == self.totalStake + getInflation(self.lastMintBlockNum, web3.eth.blockNumber+100, self.emissionPerBlock)
        

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f'Total rules executed = {self.numTxsTested-1}')
            
    
    state_machine(StateMachine, a, cfDeploy, settings=settings)