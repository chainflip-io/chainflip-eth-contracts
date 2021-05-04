from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy
from utils import *
from hypothesis import strategies as hypStrat


settings = {"stateful_step_count": 100, "max_examples": 25}


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
            self.lastMintBlockNum = self.sm.tx.blockNumber
            self.emissionPerBlock = EMISSION_PER_BLOCK
            self.totalStake = 0
            self.minStake = INIT_MIN_STAKE
            self.allAddrs = self.stakers + [self.sm]
            
            # Eth bals shouldn't change in this test, but just to be sure...
            self.ethBals = {addr: INIT_ETH_BAL if addr in a else 0 for addr in self.allAddrs}
            self.flipBals = {addr: INIT_STAKE if addr in self.stakers else 0 for addr in self.allAddrs}
            self.pendingClaims = {nodeID: NULL_CLAIM for nodeID in range(NUM_STAKERS + 1)}
            self.numTxsTested = 0


        # Variables that will be a random value with each fcn/rule called

        st_sender = strategy("address")
        st_staker = strategy("address", length=NUM_STAKERS)
        # +1 since nodeID==0 is unusable
        st_nodeID = strategy("uint", max_value=NUM_STAKERS)
        st_amount = strategy("uint", max_value=MAX_TEST_STAKE)
        st_expiry_time_diff = strategy("uint", max_value=CLAIM_DELAY*10)
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)
        # This would be 10x the initial supply in 1 year, so is a reasonable max without
        # uint overflowing
        st_emission = strategy("uint", max_value=370 * E_18)
        # In reality this high amount isn't really realistic, but for the sake of testing
        st_minStake = strategy("uint", max_value=int(INIT_STAKE/2))
        # So there's a 1% chance of a bad sig to maximise useful txs
        st_signer_agg = hypStrat.sampled_from(([AGG_SIGNER_1] * 99) + [GOV_SIGNER_1])
        st_signer_gov = hypStrat.sampled_from([AGG_SIGNER_1] + ([GOV_SIGNER_1] * 99))

        # def rule_claimBatch(self, st_signer_agg, st_nodeIDs, st_receivers, st_amounts, st_sender):

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
        def rule_registerClaim(self, st_signer_agg, st_nodeID, st_staker, st_amount, st_sender, st_expiry_time_diff):
            args = (st_nodeID, st_amount, st_staker, chain.time() + st_expiry_time_diff)
            callDataNoSig = self.sm.registerClaim.encode_input(NULL_SIG_DATA, *args)

            if st_nodeID == 0:
                print('        NODEID rule_registerClaim', *args)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.registerClaim(st_signer_agg.getSigData(callDataNoSig), *args, {'from': st_sender})
            elif st_amount == 0:
                print('        AMOUNT rule_registerClaim', *args)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.registerClaim(st_signer_agg.getSigData(callDataNoSig), *args, {'from': st_sender})
            elif st_signer_agg != AGG_SIGNER_1:
                print('        REV_MSG_SIG rule_registerClaim', *args)
                with reverts(REV_MSG_SIG):
                    self.sm.registerClaim(st_signer_agg.getSigData(callDataNoSig), *args, {'from': st_sender})
            elif chain.time() <= self.pendingClaims[st_nodeID][3]:
                print('        REV_MSG_CLAIM_EXISTS rule_registerClaim', *args)
                with reverts(REV_MSG_CLAIM_EXISTS):
                    self.sm.registerClaim(st_signer_agg.getSigData(callDataNoSig), *args, {'from': st_sender})
            elif st_expiry_time_diff <= CLAIM_DELAY:
                print('        REV_MSG_EXPIRY_TOO_SOON rule_registerClaim', *args)
                with reverts(REV_MSG_EXPIRY_TOO_SOON):
                    self.sm.registerClaim(st_signer_agg.getSigData(callDataNoSig), *args, {'from': st_sender})
            else:
                print('                    rule_registerClaim ', *args)
                tx = self.sm.registerClaim(st_signer_agg.getSigData(callDataNoSig), *args, {'from': st_sender})

                self.pendingClaims[st_nodeID] = (st_amount, st_staker, tx.timestamp + CLAIM_DELAY, args[3])


        # Sleep for a random time so that executeClaim can be called without reverting
        def rule_sleep(self, st_sleep_time):
            print('                    rule_sleep', st_sleep_time)
            chain.sleep(st_sleep_time)
        

        # Useful results are being impeded by most attempts at executeClaim not having enough
        # delay - having 2 sleep methods makes it more common aswell as this which is enough of a delay
        # in itself, since Hypothesis usually picks small values as part of shrinking
        def rule_sleep_2_days(self):
            print('                    rule_sleep_2_days')
            chain.sleep(2 * DAY)
        

        # Executes a random claim
        def rule_executeClaim(self, st_nodeID, st_sender):
            inflation = getInflation(self.lastMintBlockNum, web3.eth.blockNumber + 1, self.emissionPerBlock)
            claim = self.pendingClaims[st_nodeID]

            if not claim[2] <= chain.time() <= claim[3]:
                print('        REV_MSG_NOT_ON_TIME rule_executeClaim', st_nodeID)
                with reverts(REV_MSG_NOT_ON_TIME):
                    self.sm.executeClaim(st_nodeID, {'from': st_sender})
            elif self.flipBals[self.sm] + inflation < claim[0]:
                print('        REV_MSG_EXCEED_BAL rule_executeClaim', st_nodeID)
                with reverts(REV_MSG_EXCEED_BAL):
                    self.sm.executeClaim(st_nodeID, {'from': st_sender})
            else:
                print('                    rule_executeClaim', st_nodeID)
                tx = self.sm.executeClaim(st_nodeID, {'from': st_sender})

                self.flipBals[claim[1]] += claim[0]
                self.flipBals[self.sm] -= (claim[0] - inflation)
                self.totalStake -= (claim[0] - inflation)
                self.lastMintBlockNum = tx.blockNumber
                self.pendingClaims[st_nodeID] = NULL_CLAIM


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
                self.lastMintBlockNum = tx.blockNumber
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
            for nodeID, claim in self.pendingClaims.items():
                assert self.sm.getPendingClaim(nodeID) == claim
        

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