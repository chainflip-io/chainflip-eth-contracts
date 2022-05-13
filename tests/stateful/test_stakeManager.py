from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy
from utils import *
from hypothesis import strategies as hypStrat
from random import choice

settings = {"stateful_step_count": 100, "max_examples": 50}


# Stateful test for all functions in the StakeManager
def test_stakeManager(BaseStateMachine, state_machine, a, cfDeploy):

    NUM_STAKERS = 5
    INIT_STAKE = 10**7 * E_18
    # Setting this low because Brownie/Hypothesis 'shrinks' random
    # numbers so that they cluster near the minimum, and we want to maximise
    # the amount of non-reverted txs there are, while also allowing for some reverts
    INIT_MIN_STAKE = 1000
    MAX_TEST_STAKE = 10**6 * E_18
    INIT_FLIP_SM = 25 * 10**4 * E_18

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

            cls.stakers = a[:NUM_STAKERS]

            for staker in cls.stakers:
                cls.f.transfer(staker, INIT_STAKE, {"from": a[0]})
            # Send excess from the deployer to the zero address so that all stakers start
            # with the same balance to make the accounting simpler
            cls.f.transfer(
                "0x0000000000000000000000000000000000000001",
                cls.f.balanceOf(a[0]) - INIT_STAKE,
                {"from": a[0]},
            )

        # Reset the local versions of state to compare the contract to after every run
        def setup(self):
            self.lastSupplyBlockNumber = 0
            self.totalStake = 0
            self.minStake = INIT_MIN_STAKE
            self.allAddrs = self.stakers + [self.sm]
            self.sm.setMinStake(INIT_MIN_STAKE)

            # Eth bals shouldn't change in this test, but just to be sure...
            self.ethBals = {
                # Accounts within "a" will have INIT_ETH_BAL - gas spent in setup/deployment
                addr: addr.balance() if addr in a else 0
                for addr in self.allAddrs
            }
            self.flipBals = {
                addr: INIT_STAKE
                if addr in self.stakers
                else (INIT_FLIP_SM if addr == self.sm else 0)
                for addr in self.allAddrs
            }
            self.pendingClaims = {
                nodeID: NULL_CLAIM for nodeID in range(NUM_STAKERS + 1)
            }

            # Store initial transaction number for each of the accounts to later calculate gas spendings
            self.iniTransactionNumber = {}
            for addr in self.allAddrs:
                self.iniTransactionNumber[addr] = len(history.filter(sender=addr))

            self.numTxsTested = 0
            self.governor = cfDeploy.gov
            self.community = cfDeploy.communityKey

            self.communityGuardDisabled = self.sm.getCommunityGuard()
            self.suspended = self.sm.getSuspendedState()

        # Variables that will be a random value with each fcn/rule called

        st_sender = strategy("address")
        st_returnAddr = strategy("address")
        st_staker = strategy("address", length=NUM_STAKERS)
        # +1 since nodeID==0 is unusable
        st_nodeID = strategy("uint", max_value=NUM_STAKERS)
        st_amount = strategy("uint", max_value=MAX_TEST_STAKE)
        st_expiry_time_diff = strategy("uint", max_value=CLAIM_DELAY * 10)
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)
        # In reality this high amount isn't really realistic, but for the sake of testing
        st_minStake = strategy("uint", max_value=int(INIT_STAKE / 2))
        # So there's a 1% chance of a bad sig to maximise useful txs
        st_signer_agg = hypStrat.sampled_from(([AGG_SIGNER_1] * 99) + [GOV_SIGNER_1])
        st_signer_gov = hypStrat.sampled_from([AGG_SIGNER_1] + ([GOV_SIGNER_1] * 99))

        # Stakes a random amount from a random staker to a random nodeID
        def rule_stake(self, st_staker, st_nodeID, st_amount, st_returnAddr):
            if st_nodeID == 0:
                print(
                    "        NODEID rule_stake", st_staker, st_nodeID, st_amount / E_18
                )
                with reverts(REV_MSG_NZ_BYTES32):
                    self.f.approve(self.sm.address, st_amount, {"from": st_staker})
                    self.sm.stake(
                        st_nodeID, st_amount, st_returnAddr, {"from": st_staker}
                    )
            elif st_amount < self.minStake:
                print(
                    "        REV_MSG_MIN_STAKE rule_stake",
                    st_staker,
                    st_nodeID,
                    st_amount / E_18,
                )
                with reverts(REV_MSG_MIN_STAKE):
                    self.f.approve(self.sm.address, st_amount, {"from": st_staker})
                    self.sm.stake(
                        st_nodeID, st_amount, st_returnAddr, {"from": st_staker}
                    )
            elif st_amount > self.flipBals[st_staker]:
                print(
                    "        REV_MSG_ERC20_EXCEED_BAL rule_stake",
                    st_staker,
                    st_nodeID,
                    st_amount / E_18,
                )
                with reverts(REV_MSG_ERC20_EXCEED_BAL):
                    self.f.approve(self.sm.address, st_amount, {"from": st_staker})
                    self.sm.stake(
                        st_nodeID, st_amount, st_returnAddr, {"from": st_staker}
                    )
            else:
                print(
                    "                    rule_stake",
                    st_staker,
                    st_nodeID,
                    st_amount / E_18,
                )
                self.f.approve(self.sm.address, st_amount, {"from": st_staker})
                self.sm.stake(st_nodeID, st_amount, st_returnAddr, {"from": st_staker})

                self.flipBals[st_staker] -= st_amount
                self.flipBals[self.sm] += st_amount
                self.totalStake += st_amount

        # Claims a random amount from a random nodeID to a random recipient
        def rule_registerClaim(
            self,
            st_signer_agg,
            st_nodeID,
            st_staker,
            st_amount,
            st_sender,
            st_expiry_time_diff,
        ):
            args = (
                st_nodeID,
                st_amount,
                st_staker,
                getChainTime() + st_expiry_time_diff,
            )
            callDataNoSig = self.sm.registerClaim.encode_input(
                agg_null_sig(self.km.address, chain.id), *args
            )

            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _registerClaim")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.sm.registerClaim(
                        st_signer_agg.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        *args,
                        {"from": st_sender},
                    )
            elif st_nodeID == 0:
                print("        NODEID rule_registerClaim", *args)
                with reverts(REV_MSG_NZ_BYTES32):
                    self.sm.registerClaim(
                        st_signer_agg.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        *args,
                        {"from": st_sender},
                    )

            elif st_amount == 0:
                print("        AMOUNT rule_registerClaim", *args)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.registerClaim(
                        st_signer_agg.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        *args,
                        {"from": st_sender},
                    )
            elif st_signer_agg != AGG_SIGNER_1:
                print("        REV_MSG_SIG rule_registerClaim", *args)
                with reverts(REV_MSG_SIG):
                    self.sm.registerClaim(
                        st_signer_agg.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        *args,
                        {"from": st_sender},
                    )
            elif getChainTime() <= self.pendingClaims[st_nodeID][3]:
                print("        REV_MSG_CLAIM_EXISTS rule_registerClaim", *args)
                with reverts(REV_MSG_CLAIM_EXISTS):
                    self.sm.registerClaim(
                        st_signer_agg.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        *args,
                        {"from": st_sender},
                    )
            elif st_expiry_time_diff <= CLAIM_DELAY:
                print("        REV_MSG_EXPIRY_TOO_SOON rule_registerClaim", *args)
                with reverts(REV_MSG_EXPIRY_TOO_SOON):
                    self.sm.registerClaim(
                        st_signer_agg.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        *args,
                        {"from": st_sender},
                    )

            else:
                print("                    rule_registerClaim ", *args)
                tx = self.sm.registerClaim(
                    st_signer_agg.getSigDataWithNonces(
                        callDataNoSig, nonces, AGG, self.km.address
                    ),
                    *args,
                    {"from": st_sender},
                )

                self.pendingClaims[st_nodeID] = (
                    st_amount,
                    st_staker,
                    tx.timestamp + CLAIM_DELAY,
                    args[3],
                )

        # Sleep for a random time so that executeClaim can be called without reverting
        def rule_sleep(self, st_sleep_time):
            print("                    rule_sleep", st_sleep_time)
            chain.sleep(st_sleep_time)

        # Useful results are being impeded by most attempts at executeClaim not having enough
        # delay - having 2 sleep methods makes it more common aswell as this which is enough of a delay
        # in itself, since Hypothesis usually picks small values as part of shrinking
        def rule_sleep_2_days(self):
            print("                    rule_sleep_2_days")
            chain.sleep(2 * DAY)

        # Executes a random claim
        def rule_executeClaim(self, st_nodeID, st_sender):
            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _executeClaim")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.sm.executeClaim(st_nodeID, {"from": st_sender})
                return

            claim = self.pendingClaims[st_nodeID]

            if not claim[2] <= getChainTime() <= claim[3]:
                print("        REV_MSG_NOT_ON_TIME rule_executeClaim", st_nodeID)
                with reverts(REV_MSG_NOT_ON_TIME):
                    self.sm.executeClaim(st_nodeID, {"from": st_sender})
            elif self.flipBals[self.sm] < claim[0]:
                print("        REV_MSG_ERC20_EXCEED_BAL rule_executeClaim", st_nodeID)
                with reverts(REV_MSG_ERC20_EXCEED_BAL):
                    self.sm.executeClaim(st_nodeID, {"from": st_sender})
            else:
                print("                    rule_executeClaim", st_nodeID)
                tx = self.sm.executeClaim(st_nodeID, {"from": st_sender})

                self.flipBals[claim[1]] += claim[0]
                self.flipBals[self.sm] -= claim[0]
                self.totalStake -= claim[0]
                self.pendingClaims[st_nodeID] = NULL_CLAIM

        # Sets the minimum stake as a random value, signs with a random (probability-weighted) sig,
        # and sends the tx from a random address
        def rule_setMinStake(self, st_minStake, st_sender):
            if st_minStake == 0:
                print(
                    "        REV_MSG_NZ_UINT rule_setMinstake", st_minStake, st_sender
                )
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.setMinStake(st_minStake, {"from": st_sender})
            elif st_sender != self.governor:
                print("        REV_MSG_SIG rule_setMinstake", st_minStake, st_sender)
                with reverts(REV_MSG_GOV_GOVERNOR):
                    self.sm.setMinStake(st_minStake, {"from": st_sender})
            else:
                print("                    rule_setMinstake", st_minStake, st_sender)
                tx = self.sm.setMinStake(st_minStake, {"from": st_sender})

                self.minStake = st_minStake

        # Suspends the stake Manager if st_sender matches the governor address. It has
        # has a 1/20 chance of being the governor - don't want to suspend it too often.
        def rule_suspend(self, st_sender):
            if st_sender == self.governor:
                if self.suspended:
                    print("        REV_MSG_GOV_SUSPENDED _suspend")
                    with reverts(REV_MSG_GOV_SUSPENDED):
                        self.sm.suspend({"from": st_sender})
                else:
                    print("                    rule_suspend", st_sender)
                    self.sm.suspend({"from": st_sender})
                    self.suspended = True
            else:
                print("        REV_MSG_GOV_GOVERNOR _suspend")
                with reverts(REV_MSG_GOV_GOVERNOR):
                    self.sm.suspend({"from": st_sender})

        # Resumes the stake Manager if it is suspended. We always resume it to avoid
        # having the stakeManager suspended too often
        def rule_resume(self, st_sender):
            if self.suspended:
                if st_sender != self.governor:
                    with reverts(REV_MSG_GOV_GOVERNOR):
                        self.sm.resume({"from": st_sender})
                # Always resume
                print("                    rule_resume", st_sender)
                self.sm.resume({"from": self.governor})
                self.suspended = False
            else:
                print("        REV_MSG_GOV_NOT_SUSPENDED _resume", st_sender)
                with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                    self.sm.resume({"from": self.governor})

        # Enable community Guard
        def rule_enableCommunityGuard(self, st_sender):
            if self.communityGuardDisabled:
                if st_sender != self.community:
                    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                        self.sm.enableCommunityGuard({"from": st_sender})
                # Always enable
                print("                    rule_enableCommunityGuard", st_sender)
                self.sm.enableCommunityGuard({"from": self.community})
                self.communityGuardDisabled = False
            else:
                print(
                    "        REV_MSG_GOV_ENABLED_GUARD _enableCommunityGuard", st_sender
                )
                with reverts(REV_MSG_GOV_ENABLED_GUARD):
                    self.sm.enableCommunityGuard({"from": self.community})

        # Enable community Guard
        def rule_disableCommunityGuard(self, st_sender):
            if not self.communityGuardDisabled:
                if st_sender != self.community:
                    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                        self.sm.disableCommunityGuard({"from": st_sender})
                # Always disable
                print("                    rule_disableCommunityGuard", st_sender)
                self.sm.disableCommunityGuard({"from": self.community})
                self.communityGuardDisabled = True
            else:
                print(
                    "        REV_MSG_GOV_DISABLED_GUARD _disableCommunityGuard",
                    st_sender,
                )
                with reverts(REV_MSG_GOV_DISABLED_GUARD):
                    self.sm.disableCommunityGuard({"from": self.community})

        # Governance attemps to withdraw FLIP in case of emergency
        def rule_govWithdrawal(self, st_sender):
            if self.communityGuardDisabled:
                if st_sender != self.governor:
                    with reverts(REV_MSG_GOV_GOVERNOR):
                        self.sm.govWithdraw({"from": st_sender})

                if self.suspended:
                    flipBalsSm = self.f.balanceOf(self.sm)
                    flipBalsGov = self.f.balanceOf(self.governor)
                    print("                    rule_govWithdrawal", st_sender)
                    self.sm.govWithdraw({"from": self.governor})
                    # Governor has all the FLIP - do the checking and return the tokens for the invariant check
                    assert self.f.balanceOf(self.governor) == flipBalsGov + flipBalsSm
                    assert self.f.balanceOf(self.sm) == 0
                    self.f.transfer(self.sm, flipBalsSm, {"from": self.governor})
                else:
                    print("        REV_MSG_GOV_NOT_SUSPENDED _govWithdrawal")
                    with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                        self.sm.govWithdraw({"from": self.governor})
            else:
                print("        REV_MSG_GOV_ENABLED_GUARD _govWithdrawal")
                with reverts(REV_MSG_GOV_ENABLED_GUARD):
                    self.sm.govWithdraw({"from": self.governor})

        # Check variable(s) after every tx that shouldn't change since there's
        # no intentional way to
        def invariant_nonchangeable(self):
            self.numTxsTested += 1
            assert self.sm.getKeyManager() == self.km.address
            assert self.sm.getFLIP() == self.f.address
            assert self.sm.getGovernor() == self.governor
            assert self.sm.getCommunityKey() == self.community

        # Check all the state variables that can be changed after every tx
        def invariant_state_vars(self):
            assert self.f.getLastSupplyUpdateBlockNumber() == self.lastSupplyBlockNumber
            assert self.sm.getMinimumStake() == self.minStake
            for nodeID, claim in self.pendingClaims.items():
                assert self.sm.getPendingClaim(nodeID) == claim

        # Check all the balances of every address are as they should be after every tx
        def invariant_bals(self):
            for addr in self.allAddrs:
                assert addr.balance() == self.ethBals[
                    addr
                ] - calculateGasSpentByAddress(addr, self.iniTransactionNumber[addr])
                assert self.f.balanceOf(addr) == self.flipBals[addr]

        def invariant_governanceCommunityGuard(self):
            assert self.community == self.sm.getCommunityKey()
            assert self.communityGuardDisabled == self.sm.getCommunityGuard()
            assert self.suspended == self.sm.getSuspendedState()

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f"Total rules executed = {self.numTxsTested-1}")

    state_machine(StateMachine, a, cfDeploy, settings=settings)
