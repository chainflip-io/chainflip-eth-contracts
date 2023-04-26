from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy
from utils import *
from hypothesis import strategies as hypStrat
from random import choice
from shared_tests import *

settings = {"stateful_step_count": 100, "max_examples": 50}


# Stateful test for all functions in the StateChainGateway
def test_stateChainGateway(BaseStateMachine, state_machine, a, cfDeploy):

    NUM_FUNDERS = 5
    INIT_FUNDING = 10**7 * E_18
    # Setting this low because Brownie/Hypothesis 'shrinks' random
    # numbers so that they cluster near the minimum, and we want to maximise
    # the amount of non-reverted txs there are, while also allowing for some reverts
    INIT_MIN_FUNDING = 1000
    MAX_TEST_FUND = 10**6 * E_18
    INIT_FLIP_SM = 25 * 10**4 * E_18

    class StateMachine(BaseStateMachine):

        """
        This test calls functions from StateChainGateway in random orders. There's a NUM_FUNDERS number
        of funders that randomly `fund` and are randomly the recipients of `claim`.
        The parameters used are so that they're small enough to increase the likelihood of the same
        address being used in multiple interactions (e.g. 2  x funds then a claim etc) and large
        enough to ensure there's variety in them
        """

        # Set up the initial test conditions once
        def __init__(cls, a, cfDeploy):
            super().__init__(cls, a, cfDeploy)

            # Set the initial minFunding to be different than the default in cfDeploy

            cls.funders = a[:NUM_FUNDERS]

            for funder in cls.funders:
                cls.f.transfer(funder, INIT_FUNDING, {"from": a[0]})
            # Send excess from the deployer to the zero address so that all funders start
            # with the same balance to make the accounting simpler
            cls.f.transfer(
                "0x0000000000000000000000000000000000000001",
                cls.f.balanceOf(a[0]) - INIT_FUNDING,
                {"from": a[0]},
            )

        # Reset the local versions of state to compare the contract to after every run
        def setup(self):
            self.lastSupplyBlockNumber = 0
            self.totalFunding = 0
            self.minFunding = INIT_MIN_FUNDING
            self.allAddrs = self.funders + [self.sm]
            self.sm.setMinFunding(INIT_MIN_FUNDING, {"from": cfDeploy.gov})

            # Eth bals shouldn't change in this test, but just to be sure...
            self.nativeBals = {
                # Accounts within "a" will have INIT_NATIVE_BAL - gas spent in setup/deployment
                addr: addr.balance() if addr in a else 0
                for addr in self.allAddrs
            }
            self.flipBals = {
                addr: INIT_FUNDING
                if addr in self.funders
                else (INIT_FLIP_SM if addr == self.sm else 0)
                for addr in self.allAddrs
            }
            self.pendingClaims = {
                nodeID: NULL_CLAIM for nodeID in range(NUM_FUNDERS + 1)
            }

            # Store initial transaction number for each of the accounts to later calculate gas spendings
            self.iniTransactionNumber = {}
            for addr in self.allAddrs:
                self.iniTransactionNumber[addr] = len(history.filter(sender=addr))

            self.numTxsTested = 0
            self.governor = cfDeploy.gov
            self.community = cfDeploy.communityKey

            self.communityGuardDisabled = self.sm.getCommunityGuardDisabled()
            self.suspended = self.sm.getSuspendedState()

        # Variables that will be a random value with each fcn/rule called

        st_sender = strategy("address")
        st_returnAddr = strategy("address")
        st_funder = strategy("address", length=NUM_FUNDERS)
        # +1 since nodeID==0 is unusable
        st_nodeID = strategy("uint", max_value=NUM_FUNDERS)
        st_amount = strategy("uint", max_value=MAX_TEST_FUND)
        st_expiry_time_diff = strategy("uint", max_value=CLAIM_DELAY * 10)
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)
        # In reality this high amount isn't really realistic, but for the sake of testing
        st_minFunding = strategy("uint", max_value=int(INIT_FUNDING / 2))
        # So there's a 1% chance of a bad sig to maximise useful txs
        st_signer_agg = hypStrat.sampled_from(
            ([AGG_SIGNER_1] * 99) + [Signer.gen_signer(None, {})]
        )
        st_signer_gov = hypStrat.sampled_from(
            [AGG_SIGNER_1] + ([Signer.gen_signer(None, {})] * 99)
        )

        # Funds a random amount from a random funder to a random nodeID
        def rule_fundStateChainAccount(
            self, st_funder, st_nodeID, st_amount, st_returnAddr
        ):
            args = (st_nodeID, st_amount, st_returnAddr)
            toLog = (*args, st_funder)
            if st_nodeID == 0:
                print("        NODEID rule_fundStateChainAccount", *toLog)
                with reverts(REV_MSG_NZ_BYTES32):
                    self.f.approve(self.sm.address, st_amount, {"from": st_funder})
                    self.sm.fundStateChainAccount(*args, {"from": st_funder})
            elif st_amount < self.minFunding:
                print("        REV_MSG_MIN_FUNDING rule_fundStateChainAccount", *toLog)
                with reverts(REV_MSG_MIN_FUNDING):
                    self.f.approve(self.sm.address, st_amount, {"from": st_funder})
                    self.sm.fundStateChainAccount(*args, {"from": st_funder})
            elif st_amount > self.flipBals[st_funder]:
                print(
                    "        REV_MSG_ERC20_EXCEED_BAL rule_fundStateChainAccount",
                    *toLog,
                )
                with reverts(REV_MSG_ERC20_EXCEED_BAL):
                    self.f.approve(self.sm.address, st_amount, {"from": st_funder})
                    self.sm.fundStateChainAccount(*args, {"from": st_funder})
            else:
                print("                    rule_fundStateChainAccount", *toLog)
                self.f.approve(self.sm.address, st_amount, {"from": st_funder})
                self.sm.fundStateChainAccount(*args, {"from": st_funder})

                self.flipBals[st_funder] -= st_amount
                self.flipBals[self.sm] += st_amount
                self.totalFunding += st_amount

        # Claims a random amount from a random nodeID to a random recipient
        def rule_registerClaim(
            self,
            st_signer_agg,
            st_nodeID,
            st_funder,
            st_amount,
            st_sender,
            st_expiry_time_diff,
        ):
            args = (
                st_nodeID,
                st_amount,
                st_funder,
                getChainTime() + st_expiry_time_diff,
            )
            toLog = (*args, st_signer_agg, st_sender)

            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _registerClaim")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=st_signer_agg,
                        sender=st_sender,
                    )

            elif st_nodeID == 0:
                print("        NODEID rule_registerClaim", *toLog)
                with reverts(REV_MSG_NZ_BYTES32):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=st_signer_agg,
                        sender=st_sender,
                    )

            elif st_amount == 0:
                print("        AMOUNT rule_registerClaim", *toLog)
                with reverts(REV_MSG_NZ_UINT):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=st_signer_agg,
                        sender=st_sender,
                    )

            elif st_signer_agg != AGG_SIGNER_1:
                print("        REV_MSG_SIG rule_registerClaim", *toLog)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=st_signer_agg,
                        sender=st_sender,
                    )

            elif getChainTime() <= self.pendingClaims[st_nodeID][3]:
                print("        REV_MSG_CLAIM_EXISTS rule_registerClaim", *toLog)
                with reverts(REV_MSG_CLAIM_EXISTS):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=st_signer_agg,
                        sender=st_sender,
                    )

            elif st_expiry_time_diff <= CLAIM_DELAY:
                print("        REV_MSG_EXPIRY_TOO_SOON rule_registerClaim", *toLog)
                with reverts(REV_MSG_EXPIRY_TOO_SOON):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=st_signer_agg,
                        sender=st_sender,
                    )

            else:
                print("                    rule_registerClaim ", *toLog)
                tx = signed_call_km(
                    self.km,
                    self.sm.registerClaim,
                    *args,
                    signer=st_signer_agg,
                    sender=st_sender,
                )

                self.pendingClaims[st_nodeID] = (
                    st_amount,
                    st_funder,
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

            # Claim can be empty
            if not claim[2] <= getChainTime() or claim == NULL_CLAIM:
                print("        REV_MSG_NOT_ON_TIME rule_executeClaim", st_nodeID)
                with reverts(REV_MSG_NOT_ON_TIME):
                    self.sm.executeClaim(st_nodeID, {"from": st_sender})
            # If it's expired it won't revert regardless of the token balances
            elif self.flipBals[self.sm] < claim[0] and getChainTime() <= claim[3]:
                print("        REV_MSG_ERC20_EXCEED_BAL rule_executeClaim", st_nodeID)
                with reverts(REV_MSG_ERC20_EXCEED_BAL):
                    self.sm.executeClaim(st_nodeID, {"from": st_sender})
            else:
                print("                    rule_executeClaim", st_nodeID)
                self.sm.executeClaim(st_nodeID, {"from": st_sender})

                # Claim not expired
                if getChainTime() <= claim[3]:
                    self.flipBals[claim[1]] += claim[0]
                    self.flipBals[self.sm] -= claim[0]
                    self.totalFunding -= claim[0]

                self.pendingClaims[st_nodeID] = NULL_CLAIM

        def rule_updateFlipSupply(self, st_amount, st_signer_agg, st_sender):
            print("                    rule_updateFlipSupply", st_amount)

            currentSupply = self.f.totalSupply()
            newTotalSupply = currentSupply + st_amount + 1

            if newTotalSupply > 0:
                if st_signer_agg != AGG_SIGNER_1:
                    print("        REV_MSG_SIG rule_registerClaim", newTotalSupply)
                    with reverts(REV_MSG_SIG):
                        signed_call_km(
                            self.km,
                            self.sm.updateFlipSupply,
                            newTotalSupply,
                            0,
                            signer=st_signer_agg,
                            sender=st_sender,
                        )
                else:
                    print("                    rule_updateFlipSupply ", newTotalSupply)

                    self.lastSupplyBlockNumber += 1
                    signed_call_km(
                        self.km,
                        self.sm.updateFlipSupply,
                        newTotalSupply,
                        self.lastSupplyBlockNumber,
                        signer=st_signer_agg,
                        sender=st_sender,
                    )
                    self.flipBals[self.sm] += st_amount + 1

                    self.lastSupplyBlockNumber += 1
                    signed_call_km(
                        self.km,
                        self.sm.updateFlipSupply,
                        newTotalSupply - st_amount,
                        self.lastSupplyBlockNumber,
                        signer=st_signer_agg,
                        sender=st_sender,
                    )
                    self.flipBals[self.sm] -= st_amount

        # Sets the minimum funding as a random value, signs with a random (probability-weighted) sig,
        # and sends the tx from a random address
        def rule_setMinFunding(self, st_minFunding, st_sender):
            if st_minFunding == 0:
                print(
                    "        REV_MSG_NZ_UINT rule_setMinFunding",
                    st_minFunding,
                    st_sender,
                )
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.setMinFunding(st_minFunding, {"from": st_sender})
            elif st_sender != self.governor:
                print(
                    "        REV_MSG_SIG rule_setMinFunding", st_minFunding, st_sender
                )
                with reverts(REV_MSG_GOV_GOVERNOR):
                    self.sm.setMinFunding(st_minFunding, {"from": st_sender})
            else:
                print(
                    "                    rule_setMinFunding", st_minFunding, st_sender
                )
                self.sm.setMinFunding(st_minFunding, {"from": st_sender})

                self.minFunding = st_minFunding

        # Suspends the State Chain Gateway if st_sender matches the governor address. It has
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

        # Resumes the State Chain Gateway if it is suspended. We always resume it to avoid
        # having the stateChainGateway suspended too often
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

        # Disable community Guard
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

        # Check all the balances of every address are as they should be after every tx
        def invariant_bals(self):
            self.numTxsTested += 1
            for addr in self.allAddrs:
                assert addr.balance() == self.nativeBals[
                    addr
                ] - calculateGasSpentByAddress(addr, self.iniTransactionNumber[addr])
                assert self.f.balanceOf(addr) == self.flipBals[addr]

        # Check addresses and keys are correct after every tx
        def invariant_addresses(self):
            assert self.sm.getKeyManager() == self.km.address
            assert self.sm.getFLIP() == self.f.address
            assert self.sm.getGovernor() == self.governor
            assert self.sm.getCommunityKey() == self.community

        # Check all the state variables that can be changed after every tx
        def invariant_state_vars(self):
            assert self.community == self.sm.getCommunityKey()
            assert self.communityGuardDisabled == self.sm.getCommunityGuardDisabled()
            assert self.suspended == self.sm.getSuspendedState()
            assert (
                self.sm.getLastSupplyUpdateBlockNumber() == self.lastSupplyBlockNumber
            )
            assert self.sm.getMinimumFunding() == self.minFunding
            for nodeID, claim in self.pendingClaims.items():
                assert self.sm.getPendingClaim(nodeID) == claim

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f"Total rules executed = {self.numTxsTested-1}")

    state_machine(StateMachine, a, cfDeploy, settings=settings)
