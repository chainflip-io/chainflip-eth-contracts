from consts import *
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import strategy, contract_strategy
from brownie.convert import to_bytes
from utils import *
from hypothesis import strategies as hypStrat
from random import choice, choices
import time

settings = {
    "stateful_step_count": 100,
    "max_examples": 50,
}

# Stateful test for all functions in the Vault, KeyManager, and StakeManager
def test_all(
    BaseStateMachine,
    state_machine,
    a,
    cfDeployAllWhitelist,
    Deposit,
    Token,
    StakeManager,
    KeyManager,
    Vault,
    CFReceiverMock,
):

    # Vault
    # The max swapID to use. SwapID is needed as a salt to create a unique create2
    # address, and for ease they're used between 1 and MAX_SWAPID inclusive in this test.
    MAX_SWAPID = 5
    # The max number of addresses to send txs from. This is used both for simulating
    # users where NATIVE/tokens come out of their account (send NATIVE/tokens), and also for
    # being the sender of fcns where the sender shouldn't matter, but just needs a
    # sender (fcns that require an aggKey sig like `transfer` and `fetchDepositNative`).
    MAX_NUM_SENDERS = 5
    # The max amount of native for a 'user' to send to a deposit address, so that
    # the same user can send many more times without running out
    MAX_NATIVE_SEND = E_18
    # The max amount of tokens for a 'user' to send to a deposit address, so that
    # the same user can send many more times without running out
    MAX_TOKEN_SEND = 10**5 * E_18
    # The max amount of tokens for a 'user' to send to a deposit address, so that
    # the same user can send many more times without running out
    INIT_TOKEN_AMNT = MAX_TOKEN_SEND * 100

    # KeyManager
    # The total number of keys to have in the pool to assign and sign from
    TOTAL_KEYS = 4

    # StakeManager
    INIT_STAKE = 10**25
    # Setting this low because Brownie/Hypothesis 'shrinks' random
    # numbers so that they cluster near the minimum, and we want to maximise
    # the amount of non-reverted txs there are, while also allowing for some reverts
    INIT_MIN_STAKE = 1000
    MAX_TEST_STAKE = 10**6 * E_18
    INIT_FLIP_SM = 25 * 10**4 * E_18

    SUPPLY_BLOCK_NUMBER_RANGE = 10

    class StateMachine(BaseStateMachine):

        # Max funds in the Vault
        TOTAL_FUNDS = 10**3 * E_18

        """
        This test calls functions Vault, from KeyManager and StakeManager in random orders.

        It uses a set number of Deposit contracts/create2 addresses
        for native & each token (MAX_SWAPID amount of each, 3 * MAX_SWAPID total) and also
        randomly sends native and the 2 ERC20 tokens to the create2 addresses that
        correspond to the create2 addresses so that something can actually be fetched
        and transferred.

        Keys are attempted to be set as random keys with a random signing key - all
        keys are from a pool of the default AGG_KEY and GOV_KEY plus freshly generated
        keys at the start of each run.

        There's a MAX_NUM_SENDERS number of stakers that randomly `stake` and are randomly
        the recipients of `claim`. The parameters used are so that they're small enough
        to increase the likelihood of the same address being used in multiple
        interactions (e.g. 2  x stakes then a claim etc) and large enough to ensure
        there's variety in them.

        The parameters used are so that they're small enough to increase the likelihood of the same
        address being used in multiple interactions and large enough to ensure there's variety in them
        
        This test also deploys a new version of the following contracts: StakeManager, Vault and KeyManager

        All the references to these contracts need to be updated in the already deployed contracts.
        """

        # Set up the initial test conditions once
        def __init__(
            cls,
            a,
            cfDeployAllWhitelist,
            Deposit,
            Token,
            CFReceiverMock,
        ):
            super().__init__(cls, a, cfDeployAllWhitelist)

            cls.tokenA = a[0].deploy(
                Token, "NotAPonziA", "NAPA", INIT_TOKEN_SUPPLY * 10
            )
            cls.tokenB = a[0].deploy(
                Token, "NotAPonziB", "NAPB", INIT_TOKEN_SUPPLY * 10
            )
            cls.tokensList = (NATIVE_ADDR, cls.tokenA, cls.tokenB)

            for token in [cls.tokenA, cls.tokenB]:
                for recip in a[1:]:
                    token.transfer(recip, INIT_TOKEN_AMNT)
                # Send excess from the deployer to the zero address so that all stakers start
                # with the same balance to make the accounting simpler
                token.transfer(
                    "0x0000000000000000000000000000000000000001",
                    token.balanceOf(a[0]) - INIT_TOKEN_AMNT,
                    {"from": a[0]},
                )

            cls.create2EthAddrs = [
                getCreate2Addr(
                    cls.v.address,
                    cleanHexStrPad(swapID),
                    Deposit,
                    cleanHexStrPad(NATIVE_ADDR),
                )
                for swapID in range(0, MAX_SWAPID + 1)
            ]
            cls.create2TokenAAddrs = [
                getCreate2Addr(
                    cls.v.address,
                    cleanHexStrPad(swapID),
                    Deposit,
                    cleanHexStrPad(cls.tokenA.address),
                )
                for swapID in range(0, MAX_SWAPID + 1)
            ]
            cls.create2TokenBAddrs = [
                getCreate2Addr(
                    cls.v.address,
                    cleanHexStrPad(swapID),
                    Deposit,
                    cleanHexStrPad(cls.tokenB.address),
                )
                for swapID in range(0, MAX_SWAPID + 1)
            ]

            cls.stakers = a[:MAX_NUM_SENDERS]

            for staker in cls.stakers:
                cls.f.transfer(staker, INIT_STAKE, {"from": a[0]})
            # Send excess from the deployer to the zero address so that all stakers start
            # with the same balance to make the accounting simpler
            cls.f.transfer(
                "0x0000000000000000000000000000000000000001",
                cls.f.balanceOf(a[0]) - INIT_STAKE,
                {"from": a[0]},
            )

            # Vault - initialize with some funds
            a[3].transfer(cls.v, cls.TOTAL_FUNDS)

            # Workaround for initial contract's Balances
            initialVaultBalance = web3.eth.get_balance(cls.v.address)
            assert initialVaultBalance == cls.TOTAL_FUNDS
            initialKeyManagerBalance = web3.eth.get_balance(cls.km.address)
            initialStakeManagerBalance = web3.eth.get_balance(cls.sm.address)
            cls.initialBalancesContracts = [
                initialVaultBalance,
                initialKeyManagerBalance,
                initialStakeManagerBalance,
            ]

            # Store original contracts to be able to test upgradability
            cls.orig_sm = cls.sm
            cls.orig_v = cls.v
            cls.orig_km = cls.km

            # Deploy a CFReceiverMock
            cls.cfReceiverMock = a[0].deploy(CFReceiverMock, cls.v.address)
            cls.orig_cfRec = cls.cfReceiverMock

            assert cls.cfReceiverMock.cfVault() == cls.v.address

        # Reset the local versions of state to compare the contract to after every run
        def setup(self):

            # Set original contracts to be able to test upgradability
            self.sm = self.orig_sm
            self.v = self.orig_v
            self.km = self.orig_km
            self.cfReceiverMock = self.orig_cfRec

            self.governor = cfDeployAllWhitelist.gov
            self.communityKey = cfDeployAllWhitelist.communityKey

            self.allAddrs = self.stakers
            self.allAddrs = [
                *[addr.address for addr in self.stakers],
                *self.create2EthAddrs,
                *self.create2TokenAAddrs,
                *self.create2TokenBAddrs,
            ]

            self.sm.setMinStake(INIT_MIN_STAKE, {"from": self.governor})

            self.nativeBals = {
                # Accounts within "a" will have INIT_NATIVE_BAL - gas spent in setup/deployment
                addr: web3.eth.get_balance(str(addr)) if addr in a else 0
                for addr in self.allAddrs
            }

            # Set intial balances of remaining contracts
            contracts = [self.v, self.km, self.sm]
            self.allAddrs += contracts
            for index in range(len(contracts)):
                self.nativeBals[contracts[index]] = self.initialBalancesContracts[index]

            # Store initial transaction number for each of the accounts to later calculate gas spendings
            self.iniTransactionNumber = {}
            for addr in self.allAddrs:
                self.iniTransactionNumber[addr] = len(history.filter(sender=addr))

            # Vault
            self.tokenABals = {
                addr: INIT_TOKEN_AMNT if addr in a else 0 for addr in self.allAddrs
            }
            self.tokenBBals = {
                addr: INIT_TOKEN_AMNT if addr in a else 0 for addr in self.allAddrs
            }
            self.v_communityGuardDisabled = self.v.getCommunityGuardDisabled()
            self.v_suspended = self.v.getSuspendedState()

            # KeyManager
            self.lastValidateTime = self.deployerContract.tx.timestamp + 1
            self.keyIDToCurKeys = {AGG: AGG_SIGNER_1}
            self.allKeys = [*self.keyIDToCurKeys.values()] + (
                [Signer.gen_signer(None, {})]
                * (TOTAL_KEYS - len(self.keyIDToCurKeys.values()))
            )
            self.currentWhitelist = cfDeployAllWhitelist.whitelisted

            # StakeManager
            self.totalStake = 0
            self.minStake = INIT_MIN_STAKE
            self.flipBals = {
                addr: INIT_STAKE
                if addr in self.stakers
                else (INIT_FLIP_SM if addr == self.sm else 0)
                for addr in self.allAddrs
            }
            self.pendingClaims = {
                nodeID: NULL_CLAIM for nodeID in range(MAX_NUM_SENDERS + 1)
            }
            self.numTxsTested = 0

            self.sm_communityGuardDisabled = self.sm.getCommunityGuardDisabled()
            self.sm_suspended = self.sm.getSuspendedState()

            # Flip
            self.lastSupplyBlockNumber = 0

            # Dictionary swapID:deployedAddress
            self.deployedDeposits = dict()

        # Variables that will be a random value with each fcn/rule called

        # Vault

        st_native_amount = strategy("uint", max_value=MAX_NATIVE_SEND)
        st_native_amounts = strategy("uint[]", max_value=MAX_NATIVE_SEND)
        st_token = contract_strategy("Token")
        st_tokens = hypStrat.lists(st_token)
        st_token_amount = strategy("uint", max_value=MAX_TOKEN_SEND)
        st_swapID = strategy("uint", max_value=MAX_SWAPID)
        st_swapIDs = strategy("uint[]", max_value=MAX_SWAPID, unique=True)
        # Only want the 1st 5 addresses so that the chances of multiple
        # txs occurring from the same address is greatly increased while still
        # ensuring diversity in senders
        st_sender = strategy("address", length=MAX_NUM_SENDERS)
        st_addr = strategy("address", length=MAX_NUM_SENDERS)
        st_recip = strategy("address", length=MAX_NUM_SENDERS)
        st_recips = strategy("address[]", length=MAX_NUM_SENDERS, unique=True)
        st_dstToken = strategy("uint16")
        st_dstAddress = strategy("bytes")
        st_dstChain = strategy("uint32")
        st_message = strategy("bytes")
        st_refundAddress = strategy("bytes")
        st_dstNativeBudget = strategy("uint")

        # KeyManager

        st_sig_key_idx = strategy("uint", max_value=TOTAL_KEYS - 1)
        st_new_key_idx = strategy("uint", max_value=TOTAL_KEYS - 1)
        st_addrs = strategy("address[]", length=MAX_NUM_SENDERS, unique=True)
        st_msg_data = strategy("bytes")
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)
        st_message_govAction = strategy("bytes32")

        # StakeManager

        st_staker = strategy("address", length=MAX_NUM_SENDERS)
        st_returnAddr = strategy("address", length=MAX_NUM_SENDERS)
        st_nodeID = strategy("uint", max_value=MAX_NUM_SENDERS)
        st_amount = strategy("uint", max_value=MAX_TEST_STAKE)
        st_expiry_time_diff = strategy("uint", max_value=CLAIM_DELAY * 10)
        # In reality this high amount isn't really realistic, but for the sake of testing
        st_minStake = strategy("uint", max_value=int(INIT_STAKE / 2))

        # FLIP
        st_amount_supply = strategy(
            "int", min_value=-MAX_TOKEN_SEND, max_value=MAX_TOKEN_SEND
        )

        blockNumber_incr = strategy(
            "int",
            min_value=-SUPPLY_BLOCK_NUMBER_RANGE,
            max_value=SUPPLY_BLOCK_NUMBER_RANGE * 10,
        )

        # Vault

        def rule_allBatch(self, st_swapIDs, st_recips, st_native_amounts, st_sender):
            fetchTokens = choices(self.tokensList, k=len(st_swapIDs))
            fetchEthTotal = sum(
                self.nativeBals[
                    getCreate2Addr(
                        self.v.address,
                        cleanHexStrPad(st_swapIDs[i]),
                        Deposit,
                        cleanHexStrPad(NATIVE_ADDR),
                    )
                ]
                if st_swapIDs[i] not in self.deployedDeposits
                else self.nativeBals[self.deployedDeposits[st_swapIDs[i]]]
                for i, x in enumerate(fetchTokens)
                if x == NATIVE_ADDR
            )
            fetchTokenATotal = sum(
                self.tokenABals[
                    getCreate2Addr(
                        self.v.address,
                        cleanHexStrPad(st_swapIDs[i]),
                        Deposit,
                        cleanHexStrPad(self.tokenA.address),
                    )
                ]
                if st_swapIDs[i] not in self.deployedDeposits
                else self.tokenABals[self.deployedDeposits[st_swapIDs[i]]]
                for i, x in enumerate(fetchTokens)
                if x == self.tokenA
            )
            fetchTokenBTotal = sum(
                self.tokenBBals[
                    getCreate2Addr(
                        self.v.address,
                        cleanHexStrPad(st_swapIDs[i]),
                        Deposit,
                        cleanHexStrPad(self.tokenB.address),
                    )
                ]
                if st_swapIDs[i] not in self.deployedDeposits
                else self.tokenBBals[self.deployedDeposits[st_swapIDs[i]]]
                for i, x in enumerate(fetchTokens)
                if x == self.tokenB
            )

            tranMinLen = trimToShortest([st_recips, st_native_amounts])
            tranTokens = choices(self.tokensList, k=tranMinLen)
            tranTotals = {}
            validEthIdxs = getValidTranIdxs(
                tranTokens,
                st_native_amounts,
                self.nativeBals[self.v] + fetchEthTotal,
                NATIVE_ADDR,
            )
            tranTotals[NATIVE_ADDR] = sum(
                [
                    st_native_amounts[i]
                    for i, x in enumerate(tranTokens)
                    if x == NATIVE_ADDR and i in validEthIdxs
                ]
            )
            validTokAIdxs = getValidTranIdxs(
                tranTokens,
                st_native_amounts,
                self.tokenABals[self.v] + fetchTokenATotal,
                self.tokenA,
            )
            tranTotals[self.tokenA] = sum(
                [
                    st_native_amounts[i]
                    for i, x in enumerate(tranTokens)
                    if x == self.tokenA and i in validTokAIdxs
                ]
            )

            validTokBIdxs = getValidTranIdxs(
                tranTokens,
                st_native_amounts,
                self.tokenBBals[self.v] + fetchTokenBTotal,
                self.tokenB,
            )
            tranTotals[self.tokenB] = sum(
                [
                    st_native_amounts[i]
                    for i, x in enumerate(tranTokens)
                    if x == self.tokenB and i in validTokBIdxs
                ]
            )

            fetchParamsArray = []
            deployFetchParamsArray = []

            for swapID, token in zip(st_swapIDs, fetchTokens):
                if swapID in self.deployedDeposits:
                    fetchParamsArray.append([self.deployedDeposits[swapID], token])
                else:
                    deployFetchParamsArray.append([swapID, token])

            transferParams = craftTransferParamsArray(
                tranTokens, st_recips, st_native_amounts
            )

            args = (deployFetchParamsArray, fetchParamsArray, transferParams)
            toLog = (*args, fetchTokens, st_sender)

            signer = self._get_key_prob(AGG)

            if self.v_suspended:
                print("        REV_MSG_GOV_SUSPENDED _allBatch")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km, self.v.allBatch, *args, signer=signer, sender=st_sender
                    )

            elif not self.v in self.currentWhitelist:
                print("        REV_MSG_WHITELIST rule_allBatch", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km, self.v.allBatch, *args, signer=signer, sender=st_sender
                    )

            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_allBatch", signer)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km, self.v.allBatch, *args, signer=signer, sender=st_sender
                    )

            else:
                tx = signed_call_km(
                    self.km, self.v.allBatch, *args, signer=signer, sender=st_sender
                )

                if (
                    tranTotals[self.tokenA] - fetchTokenATotal > self.tokenABals[self.v]
                    or tranTotals[self.tokenB] - fetchTokenBTotal
                    > self.tokenBBals[self.v]
                ):
                    print("        NOT ENOUGH TOKENS IN VAULT rule_allBatch", *toLog)
                    assert len(tx.events["TransferTokenFailed"]) >= 1

                else:
                    print("                    rule_allBatch", *toLog)

                self.lastValidateTime = tx.timestamp

                # Alter bals from the fetch
                for swapID, tok in zip(st_swapIDs, fetchTokens):
                    if swapID in self.deployedDeposits.keys():
                        addr = self.deployedDeposits[swapID]
                    else:
                        if tok == NATIVE_ADDR:
                            addr = getCreate2Addr(
                                self.v.address,
                                cleanHexStrPad(swapID),
                                Deposit,
                                cleanHexStrPad(NATIVE_ADDR),
                            )
                        else:
                            addr = getCreate2Addr(
                                self.v.address,
                                cleanHexStrPad(swapID),
                                Deposit,
                                cleanHexStrPad(tok.address),
                            )
                        self.deployedDeposits[swapID] = addr

                    if tok == NATIVE_ADDR:
                        self.nativeBals[self.v] += self.nativeBals[addr]
                        self.nativeBals[addr] = 0
                    else:
                        if tok == self.tokenA:
                            self.tokenABals[self.v] += self.tokenABals[addr]
                            self.tokenABals[addr] = 0
                        elif tok == self.tokenB:
                            self.tokenBBals[self.v] += self.tokenBBals[addr]
                            self.tokenBBals[addr] = 0
                        else:
                            assert False, "Panicc"

                # Alter bals from the transfers
                for i, (tok, rec, am) in enumerate(
                    zip(tranTokens, st_recips, st_native_amounts)
                ):
                    if tok == NATIVE_ADDR:
                        if i in validEthIdxs:
                            self.nativeBals[rec] += am
                            self.nativeBals[self.v] -= am
                    elif tok == self.tokenA:
                        if i in validTokAIdxs:
                            self.tokenABals[rec] += am
                            self.tokenABals[self.v] -= am
                    elif tok == self.tokenB:
                        if i in validTokBIdxs:
                            self.tokenBBals[rec] += am
                            self.tokenBBals[self.v] -= am
                    else:
                        assert False, "Panic"

        # Transfers native or tokens out the vault. Want this to be called by rule_vault_transfer_native
        # etc individually and not directly since they're all the same just with a different tokenAddr
        # input
        def _vault_transfer(
            self, bals, tokenAddr, st_sender, st_recip, st_native_amount
        ):
            args = [[tokenAddr, st_recip, st_native_amount]]
            signer = self._get_key_prob(AGG)
            toLog = (*args, signer, st_sender)

            if self.v_suspended:
                print("        REV_MSG_GOV_SUSPENDED _vault_transfer")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km, self.v.transfer, *args, signer=signer, sender=st_sender
                    )

            elif st_native_amount == 0:
                print("        REV_MSG_NZ_UINT _vault_transfer", *toLog)
                with reverts(REV_MSG_NZ_UINT):
                    signed_call_km(
                        self.km, self.v.transfer, *args, signer=signer, sender=st_sender
                    )
            elif not self.v in self.currentWhitelist:
                print("        REV_MSG_WHITELIST _vault_transfer", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km, self.v.transfer, *args, signer=signer, sender=st_sender
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG _vault_transfer", signer)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km, self.v.transfer, *args, signer=signer, sender=st_sender
                    )
            else:
                tx = signed_call_km(
                    self.km, self.v.transfer, *args, signer=signer, sender=st_sender
                )
                self.lastValidateTime = tx.timestamp

                if bals[self.v] < st_native_amount:
                    if tokenAddr != NATIVE_ADDR:
                        print(
                            "        NOT ENOUGH TOKENS IN VAULT _vault_transfer", *toLog
                        )
                        assert len(tx.events["TransferTokenFailed"]) == 1
                    else:
                        print(
                            "        NOT ENOUGH NATIVE IN VAULT _vault_transfer", *toLog
                        )
                        assert len(tx.events["TransferNativeFailed"]) == 1
                else:
                    print("                    _vault_transfer", *toLog)

                    bals[self.v] -= st_native_amount
                    bals[st_recip] += st_native_amount

        def rule_vault_transfer_native(self, st_sender, st_recip, st_native_amount):
            self._vault_transfer(
                self.nativeBals, NATIVE_ADDR, st_sender, st_recip, st_native_amount
            )

        def rule_vault_transfer_tokenA(self, st_sender, st_recip, st_token_amount):
            self._vault_transfer(
                self.tokenABals, self.tokenA, st_sender, st_recip, st_token_amount
            )

        def rule_vault_transfer_tokenB(self, st_sender, st_recip, st_token_amount):
            self._vault_transfer(
                self.tokenBBals, self.tokenB, st_sender, st_recip, st_token_amount
            )

        # Send any combination of native/tokenA/tokenB out of the vault. Using st_native_amounts
        # for both native amounts and token amounts here because its max is within the bounds of
        # both native and tokens.
        def rule_vault_transferBatch(self, st_sender, st_recips, st_native_amounts):
            signer = self._get_key_prob(AGG)
            minLen = trimToShortest([st_recips, st_native_amounts])
            tokens = choices([NATIVE_ADDR, self.tokenA, self.tokenB], k=minLen)
            args = [craftTransferParamsArray(tokens, st_recips, st_native_amounts)]
            toLog = (*args, st_sender, signer)

            totalEth = 0
            totalTokenA = 0
            totalTokenB = 0
            validEthIdxs = getValidTranIdxs(
                tokens, st_native_amounts, self.nativeBals[self.v], NATIVE_ADDR
            )
            validTokAIdxs = getValidTranIdxs(
                tokens, st_native_amounts, self.tokenABals[self.v], self.tokenA
            )
            validTokBIdxs = getValidTranIdxs(
                tokens, st_native_amounts, self.tokenBBals[self.v], self.tokenB
            )
            for i, (tok, am) in enumerate(zip(tokens, st_native_amounts)):
                if tok == NATIVE_ADDR:
                    if i in validEthIdxs:
                        totalEth += am
                elif tok == self.tokenA:
                    if i in validTokAIdxs:
                        totalTokenA += am
                elif tok == self.tokenB:
                    if i in validTokBIdxs:
                        totalTokenB += am
                else:
                    assert False, "Unknown asset"

            if self.v_suspended:
                print("        REV_MSG_GOV_SUSPENDED _vault_transferBatch")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.v.transferBatch,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

            elif not self.v in self.currentWhitelist:
                print("        REV_MSG_WHITELIST rule_vault_transferBatch", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km,
                        self.v.transferBatch,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_vault_transferBatch", *toLog)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.v.transferBatch,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

            else:
                tx = signed_call_km(
                    self.km,
                    self.v.transferBatch,
                    *args,
                    signer=signer,
                    sender=st_sender,
                )

                if (
                    totalTokenA > self.tokenABals[self.v]
                    or totalTokenB > self.tokenBBals[self.v]
                ):
                    print(
                        "        NOT ENOUGH TOKENS IN VAULT rule_vault_transferBatch",
                        *toLog,
                    )
                    assert len(tx.events["TransferTokenFailed"]) >= 1

                else:
                    print("                    rule_vault_transferBatch", *toLog)

                    self.lastValidateTime = tx.timestamp
                    for i in range(len(st_recips)):
                        if tokens[i] == NATIVE_ADDR:
                            if i in validEthIdxs:
                                self.nativeBals[st_recips[i]] += st_native_amounts[i]
                                self.nativeBals[self.v] -= st_native_amounts[i]
                        elif tokens[i] == self.tokenA:
                            if i in validTokAIdxs:
                                self.tokenABals[st_recips[i]] += st_native_amounts[i]
                                self.tokenABals[self.v] -= st_native_amounts[i]
                        elif tokens[i] == self.tokenB:
                            if i in validTokBIdxs:
                                self.tokenBBals[st_recips[i]] += st_native_amounts[i]
                                self.tokenBBals[self.v] -= st_native_amounts[i]
                        else:
                            assert False, "Panic"

        # Transfers native from a user/sender to one of the depositEth create2 addresses
        def rule_transfer_native_to_depositEth(
            self, st_sender, st_swapID, st_native_amount
        ):
            # No point testing reverts of these conditions since it's not what we're trying to test
            if st_swapID != 0 and self.nativeBals[st_sender] >= st_native_amount:
                print(
                    "                    rule_transfer_native_to_depositEth",
                    st_sender,
                    st_swapID,
                    st_native_amount,
                )
                depositAddr = getCreate2Addr(
                    self.v.address,
                    cleanHexStrPad(st_swapID),
                    Deposit,
                    cleanHexStrPad(NATIVE_ADDR),
                )
                st_sender.transfer(depositAddr, st_native_amount)

                self.nativeBals[st_sender] -= st_native_amount
                self.nativeBals[depositAddr] += st_native_amount

        # Transfers a token from a user/sender to one of the depositEth create2 addresses.
        # This isn't called directly since rule_transfer_tokens_to_depositTokenA etc use it
        # in the same way but with a different tokenAddr
        def _transfer_tokens_to_token_deposit(
            self, bals, token, st_sender, st_swapID, st_token_amount
        ):
            # No point testing reverts of these conditions since it's not what we're trying to test
            if st_swapID != 0 and bals[st_sender] >= st_token_amount:
                print(
                    "                    _transfer_tokens_to_token_deposit",
                    token,
                    st_sender,
                    st_swapID,
                    st_token_amount,
                )
                depositAddr = getCreate2Addr(
                    self.v.address,
                    cleanHexStrPad(st_swapID),
                    Deposit,
                    cleanHexStrPad(token.address),
                )
                token.transfer(depositAddr, st_token_amount, {"from": st_sender})

                bals[st_sender] -= st_token_amount
                bals[depositAddr] += st_token_amount

        # Deposits tokenA from a user to a tokenA create2
        def rule_transfer_tokens_to_depositTokenA(
            self, st_sender, st_swapID, st_token_amount
        ):
            self._transfer_tokens_to_token_deposit(
                self.tokenABals, self.tokenA, st_sender, st_swapID, st_token_amount
            )

        # Deposits tokenB from a user to a tokenB create2
        def rule_transfer_tokens_to_depositTokenB(
            self, st_sender, st_swapID, st_token_amount
        ):
            self._transfer_tokens_to_token_deposit(
                self.tokenBBals, self.tokenB, st_sender, st_swapID, st_token_amount
            )

        # Fetch the native deposit of a random create2
        def rule_fetchNative(self, st_sender, st_swapID):
            signer = self._get_key_prob(AGG)
            toLog = (st_swapID, signer, st_sender)

            if self.v_suspended:
                print("        REV_MSG_GOV_SUSPENDED _fetchDepositNative")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        [[st_swapID, NATIVE_ADDR]],
                        signer=signer,
                        sender=st_sender,
                    )
            elif not self.v in self.currentWhitelist:
                print("        REV_MSG_WHITELIST rule_fetchDepositNative", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        [[st_swapID, NATIVE_ADDR]],
                        signer=signer,
                        sender=st_sender,
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_fetchDepositNative", signer)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        [[st_swapID, NATIVE_ADDR]],
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                print("                    rule_fetchDepositNative", *toLog)

                if st_swapID not in self.deployedDeposits:
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        [[st_swapID, NATIVE_ADDR]],
                        signer=signer,
                        sender=st_sender,
                    )

                    depositAddr = getCreate2Addr(
                        self.v.address,
                        cleanHexStrPad(st_swapID),
                        Deposit,
                        cleanHexStrPad(NATIVE_ADDR),
                    )
                    self.deployedDeposits[st_swapID] = depositAddr
                else:
                    depositAddr = self.deployedDeposits[st_swapID]
                    signed_call_km(
                        self.km,
                        self.v.fetchBatch,
                        [[depositAddr, NATIVE_ADDR]],
                        signer=signer,
                        sender=st_sender,
                    )

                depositBal = self.nativeBals[depositAddr]
                tx = signed_call_km(
                    self.km,
                    self.v.fetchBatch,
                    [[depositAddr, NATIVE_ADDR]],
                    signer=signer,
                    sender=st_sender,
                )

                self.nativeBals[depositAddr] -= depositBal
                self.nativeBals[self.v] += depositBal
                self.lastValidateTime = tx.timestamp

        def rule_fetchDepositNativeBatch(self, st_sender, st_swapIDs):

            signer = self._get_key_prob(AGG)
            toLog = (st_swapIDs, signer, st_sender)

            if self.v_suspended:
                print("        REV_MSG_GOV_SUSPENDED _fetchDepositNativeBatch")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        craftDeployFetchParamsArray(
                            st_swapIDs, [NATIVE_ADDR] * len(st_swapIDs)
                        ),
                        signer=signer,
                        sender=st_sender,
                    )
            elif not self.v in self.currentWhitelist:
                print("        REV_MSG_WHITELIST rule_fetchDepositNativeBatch", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        craftDeployFetchParamsArray(
                            st_swapIDs, [NATIVE_ADDR] * len(st_swapIDs)
                        ),
                        signer=signer,
                        sender=st_sender,
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_fetchDepositNativeBatch", *toLog)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        craftDeployFetchParamsArray(
                            st_swapIDs, [NATIVE_ADDR] * len(st_swapIDs)
                        ),
                        signer=signer,
                        sender=st_sender,
                    )
            else:

                print("                    rule_fetchDepositNativeBatch", *toLog)

                used_addresses = []
                non_used_swapIDs = []
                for st_swapID in st_swapIDs:
                    if st_swapID in self.deployedDeposits:
                        depositAddr = self.deployedDeposits[st_swapID]
                        used_addresses.append(depositAddr)

                    else:
                        non_used_swapIDs.append(st_swapID)
                        depositAddr = getCreate2Addr(
                            self.v.address,
                            cleanHexStrPad(st_swapID),
                            Deposit,
                            cleanHexStrPad(NATIVE_ADDR),
                        )
                        self.deployedDeposits[st_swapID] = depositAddr

                    # Accounting here to reuse the loop logic
                    self.nativeBals[self.v] += self.nativeBals[depositAddr]
                    self.nativeBals[depositAddr] = 0

                deployFetchParamsArray = craftDeployFetchParamsArray(
                    non_used_swapIDs, [NATIVE_ADDR] * len(non_used_swapIDs)
                )

                signed_call_km(
                    self.km,
                    self.v.deployAndFetchBatch,
                    deployFetchParamsArray,
                    signer=signer,
                    sender=st_sender,
                )

                fetchParamsArray = craftFetchParamsArray(
                    used_addresses, [NATIVE_ADDR] * len(used_addresses)
                )
                tx = signed_call_km(
                    self.km,
                    self.v.fetchBatch,
                    fetchParamsArray,
                    signer=signer,
                    sender=st_sender,
                )

                self.lastValidateTime = tx.timestamp

        # Fetch the token deposit of a random create2
        def _fetchDepositToken(self, bals, token, st_sender, st_swapID):
            args = [[st_swapID, token.address]]
            signer = self._get_key_prob(AGG)
            toLog = (*args, signer, st_sender)
            if self.v_suspended:
                print("        REV_MSG_GOV_SUSPENDED _fetchDepositToken")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif not self.v in self.currentWhitelist:
                print("        REV_MSG_WHITELIST _fetchDepositToken", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG _fetchDepositToken", signer)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                print("                    _fetchDepositToken", *toLog)

                if st_swapID not in self.deployedDeposits:
                    tx = signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        args,
                        signer=signer,
                        sender=st_sender,
                    )
                    depositAddr = getCreate2Addr(
                        self.v.address,
                        cleanHexStrPad(st_swapID),
                        Deposit,
                        cleanHexStrPad(token.address),
                    )
                    self.deployedDeposits[st_swapID] = depositAddr
                else:
                    depositAddr = self.deployedDeposits[st_swapID]
                    tx = signed_call_km(
                        self.km,
                        self.v.fetchBatch,
                        [[depositAddr, token.address]],
                        signer=signer,
                        sender=st_sender,
                    )

                depositBal = bals[depositAddr]
                bals[depositAddr] -= depositBal
                bals[self.v] += depositBal
                self.lastValidateTime = tx.timestamp

        # Fetch the tokenA deposit of a random create2
        def rule_fetchDepositToken_tokenA(self, st_sender, st_swapID):
            self._fetchDepositToken(self.tokenABals, self.tokenA, st_sender, st_swapID)

        # Fetch the tokenB deposit of a random create2
        def rule_fetchDepositToken_tokenB(self, st_sender, st_swapID):
            self._fetchDepositToken(self.tokenBBals, self.tokenB, st_sender, st_swapID)

        def rule_fetchDepositTokenBatch(self, st_sender, st_swapIDs, st_tokens):
            trimToShortest([st_swapIDs, st_tokens])
            signer = self._get_key_prob(AGG)
            args = [craftDeployFetchParamsArray(st_swapIDs, st_tokens)]
            toLog = (*args, signer, st_sender)

            if self.v_suspended:
                print("        REV_MSG_GOV_SUSPENDED _fetchDepositTokenBatch")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif not self.v in self.currentWhitelist:
                print("        REV_MSG_WHITELIST rule_fetchDepositTokenBatch", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_fetchDepositTokenBatch", signer)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.v.deployAndFetchBatch,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                fetchParamsArray = []
                deployFetchParamsArray = []

                for st_swapID, token in zip(st_swapIDs, st_tokens):
                    if st_swapID in self.deployedDeposits:
                        fetchParamsArray.append(
                            [self.deployedDeposits[st_swapID], token.address]
                        )
                        depositAddr = self.deployedDeposits[st_swapID]

                    else:
                        deployFetchParamsArray.append([st_swapID, token.address])
                        depositAddr = getCreate2Addr(
                            self.v.address,
                            cleanHexStrPad(st_swapID),
                            Deposit,
                            cleanHexStrPad(token.address),
                        )
                        self.deployedDeposits[st_swapID] = depositAddr

                    # Accounting here to reuse the loop logic
                    if token == self.tokenA:
                        self.tokenABals[self.v] += self.tokenABals[depositAddr]
                        self.tokenABals[depositAddr] = 0
                    elif token == self.tokenB:
                        self.tokenBBals[self.v] += self.tokenBBals[depositAddr]
                        self.tokenBBals[depositAddr] = 0
                    else:
                        assert False, "Panicc"

                print("                    rule_fetchDepositTokenBatch", *toLog)
                signed_call_km(
                    self.km,
                    self.v.deployAndFetchBatch,
                    deployFetchParamsArray,
                    signer=signer,
                    sender=st_sender,
                )

                tx = signed_call_km(
                    self.km,
                    self.v.fetchBatch,
                    fetchParamsArray,
                    signer=signer,
                    sender=st_sender,
                )
                self.lastValidateTime = tx.timestamp

        # Swap Native
        def rule_xSwapNative(
            self, st_sender, st_dstToken, st_dstAddress, st_native_amount, st_dstChain
        ):
            args = (st_dstChain, st_dstAddress, st_dstToken)
            toLog = (*args, st_sender)
            if self.v_suspended:
                with reverts(REV_MSG_GOV_SUSPENDED):
                    print("        REV_MSG_GOV_SUSPENDED _xSwapNative")
                    self.v.xSwapNative(*args, {"from": st_sender})
            else:
                if st_native_amount == 0:
                    print("        REV_MSG_NZ_UINT _xSwapNative", *toLog)
                    with reverts(REV_MSG_NZ_UINT):
                        self.v.xSwapNative(
                            *args,
                            {"from": st_sender, "amount": st_native_amount},
                        )
                else:
                    if web3.eth.get_balance(str(st_sender)) >= st_native_amount:
                        print("                    rule_xSwapNative", *toLog)
                        tx = self.v.xSwapNative(
                            *args,
                            {"from": st_sender, "amount": st_native_amount},
                        )
                        assert (
                            web3.eth.get_balance(self.v.address)
                            == self.nativeBals[self.v] + st_native_amount
                        )
                        self.nativeBals[self.v] += st_native_amount
                        self.nativeBals[st_sender] -= st_native_amount
                        assert tx.events["SwapNative"][0].values() == [
                            st_dstChain,
                            hexStr(st_dstAddress),
                            st_dstToken,
                            st_native_amount,
                            st_sender,
                        ]

        # Swap Token
        def rule_xSwapToken(
            self,
            st_sender,
            st_dstToken,
            st_dstAddress,
            st_token_amount,
            st_token,
            st_dstChain,
        ):
            args = (
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                st_token,
                st_token_amount,
            )
            toLog = (*args, st_sender)
            if self.v_suspended:
                with reverts(REV_MSG_GOV_SUSPENDED):
                    print("        REV_MSG_GOV_SUSPENDED _swapToken")
                    self.v.xSwapToken(
                        *args,
                        {"from": st_sender},
                    )
            else:
                if st_token_amount == 0:
                    print("        REV_MSG_NZ_UINT _swapToken", *toLog)
                    with reverts(REV_MSG_NZ_UINT):
                        self.v.xSwapToken(
                            *args,
                            {"from": st_sender},
                        )
                else:
                    st_token.approve(self.v, st_token_amount, {"from": st_sender})
                    if st_token.balanceOf(st_sender) < st_token_amount:
                        print("        REV_MSG_ERC20_EXCEED_BAL _swapToken", *toLog)
                        with reverts(REV_MSG_ERC20_EXCEED_BAL):
                            self.v.xSwapToken(
                                *args,
                                {"from": st_sender},
                            )
                    else:
                        print("                    rule_swapToken", *toLog)
                        tx = self.v.xSwapToken(
                            *args,
                            {"from": st_sender},
                        )

                        if st_token == self.tokenA:
                            assert (
                                st_token.balanceOf(self.v.address)
                                == self.tokenABals[self.v] + st_token_amount
                            )
                            self.tokenABals[self.v] += st_token_amount
                            self.tokenABals[st_sender] -= st_token_amount
                        elif st_token == self.tokenB:
                            assert (
                                st_token.balanceOf(self.v.address)
                                == self.tokenBBals[self.v] + st_token_amount
                            )
                            self.tokenBBals[self.v] += st_token_amount
                            self.tokenBBals[st_sender] -= st_token_amount
                        else:
                            assert False, "Panicc"

                        assert tx.events["SwapToken"][0].values() == [
                            st_dstChain,
                            hexStr(st_dstAddress),
                            st_dstToken,
                            st_token,
                            st_token_amount,
                            st_sender,
                        ]

        def rule_xCallNative(
            self,
            st_sender,
            st_dstToken,
            st_dstAddress,
            st_native_amount,
            st_dstChain,
            st_message,
            st_dstNativeBudget,
            st_refundAddress,
        ):
            args = (
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                st_message,
                st_dstNativeBudget,
                st_refundAddress,
            )
            toLog = (*args, st_sender)
            if self.v_suspended:
                with reverts(REV_MSG_GOV_SUSPENDED):
                    print(
                        "        REV_MSG_GOV_SUSPENDED _xCallNative",
                    )
                    self.v.xCallNative(*args, {"from": st_sender})
            else:
                if st_native_amount == 0:
                    print("        REV_MSG_NZ_UINT _xCallNative", *toLog)
                    with reverts(REV_MSG_NZ_UINT):
                        self.v.xCallNative(
                            *args,
                            {"from": st_sender, "amount": st_native_amount},
                        )
                else:
                    if web3.eth.get_balance(str(st_sender)) >= st_native_amount:
                        print("                    rule_xCallNative", *toLog)
                        tx = self.v.xCallNative(
                            *args,
                            {"from": st_sender, "amount": st_native_amount},
                        )
                        assert (
                            web3.eth.get_balance(self.v.address)
                            == self.nativeBals[self.v] + st_native_amount
                        )
                        self.nativeBals[self.v] += st_native_amount
                        self.nativeBals[st_sender] -= st_native_amount
                        assert tx.events["XCallNative"][0].values() == [
                            st_dstChain,
                            hexStr(st_dstAddress),
                            st_dstToken,
                            st_native_amount,
                            st_sender,
                            hexStr(st_message),
                            st_dstNativeBudget,
                            hexStr(st_refundAddress),
                        ]

        def rule_xCallToken(
            self,
            st_sender,
            st_dstToken,
            st_dstAddress,
            st_token_amount,
            st_token,
            st_dstChain,
            st_message,
            st_dstNativeBudget,
            st_refundAddress,
        ):
            args = (
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                st_message,
                st_dstNativeBudget,
                st_token,
                st_token_amount,
                st_refundAddress,
            )
            toLog = (*args, st_sender)
            if self.v_suspended:
                with reverts(REV_MSG_GOV_SUSPENDED):
                    print("        REV_MSG_GOV_SUSPENDED _xCallToken")
                    self.v.xCallToken(
                        *args,
                        {"from": st_sender},
                    )
            else:
                if st_token_amount == 0:
                    print("        REV_MSG_NZ_UINT _xCallToken", *toLog)
                    with reverts(REV_MSG_NZ_UINT):
                        self.v.xCallToken(
                            *args,
                            {"from": st_sender},
                        )
                else:
                    st_token.approve(self.v, st_token_amount, {"from": st_sender})
                    if st_token.balanceOf(st_sender) < st_token_amount:
                        print("        REV_MSG_ERC20_EXCEED_BAL _xCallToken", *toLog)
                        with reverts(REV_MSG_ERC20_EXCEED_BAL):
                            self.v.xCallToken(
                                *args,
                                {"from": st_sender},
                            )
                    else:
                        print("                    rule_xCallToken", *toLog)
                        tx = self.v.xCallToken(
                            *args,
                            {"from": st_sender},
                        )

                        if st_token == self.tokenA:
                            assert (
                                st_token.balanceOf(self.v.address)
                                == self.tokenABals[self.v] + st_token_amount
                            )
                            self.tokenABals[self.v] += st_token_amount
                            self.tokenABals[st_sender] -= st_token_amount
                        elif st_token == self.tokenB:
                            assert (
                                st_token.balanceOf(self.v.address)
                                == self.tokenBBals[self.v] + st_token_amount
                            )
                            self.tokenBBals[self.v] += st_token_amount
                            self.tokenBBals[st_sender] -= st_token_amount
                        else:
                            assert False, "Panicc"

                        assert tx.events["XCallToken"][0].values() == [
                            st_dstChain,
                            hexStr(st_dstAddress),
                            st_dstToken,
                            st_token,
                            st_token_amount,
                            st_sender,
                            hexStr(st_message),
                            st_dstNativeBudget,
                            hexStr(st_refundAddress),
                        ]

        # addGasNative
        def rule_addGasNative(self, st_sender, st_swapID, st_native_amount):
            st_swapID = to_bytes(st_swapID, type_str="bytes32")

            toLog = (st_swapID, st_sender)
            if self.v_suspended:
                with reverts(REV_MSG_GOV_SUSPENDED):
                    print("        REV_MSG_GOV_SUSPENDED _addGasNative")
                    self.v.addGasNative(st_swapID, {"from": st_sender})
            else:
                if web3.eth.get_balance(str(st_sender)) >= st_native_amount:
                    print("                    rule_addGasNative", *toLog)
                    tx = self.v.addGasNative(
                        st_swapID,
                        {"from": st_sender, "amount": st_native_amount},
                    )
                    assert (
                        web3.eth.get_balance(self.v.address)
                        == self.nativeBals[self.v] + st_native_amount
                    )
                    self.nativeBals[self.v] += st_native_amount
                    self.nativeBals[st_sender] -= st_native_amount
                    assert tx.events["AddGasNative"][0].values() == [
                        hexStr(st_swapID),
                        st_native_amount,
                    ]

        # addGasToken
        def rule_addGasToken(
            self,
            st_sender,
            st_swapID,
            st_token_amount,
            st_token,
        ):
            st_swapID = to_bytes(st_swapID, type_str="bytes32")

            args = (
                st_swapID,
                st_token_amount,
                st_token,
            )
            toLog = (*args, st_sender)
            if self.v_suspended:
                with reverts(REV_MSG_GOV_SUSPENDED):
                    print("        REV_MSG_GOV_SUSPENDED _addGasToken")
                    self.v.addGasToken(
                        *args,
                        {"from": st_sender},
                    )
            else:
                if st_token_amount == 0:
                    print("        REV_MSG_NZ_UINT _addGasToken", *toLog)
                    with reverts(REV_MSG_NZ_UINT):
                        self.v.addGasToken(
                            *args,
                            {"from": st_sender},
                        )
                else:
                    st_token.approve(self.v, st_token_amount, {"from": st_sender})
                    if st_token.balanceOf(st_sender) < st_token_amount:
                        print("        REV_MSG_ERC20_EXCEED_BAL _addGasToken", *toLog)
                        with reverts(REV_MSG_ERC20_EXCEED_BAL):
                            self.v.addGasToken(
                                *args,
                                {"from": st_sender},
                            )
                    else:
                        print("                    rule_addGasToken", *toLog)
                        tx = self.v.addGasToken(
                            *args,
                            {"from": st_sender},
                        )

                        if st_token == self.tokenA:
                            assert (
                                st_token.balanceOf(self.v.address)
                                == self.tokenABals[self.v] + st_token_amount
                            )
                            self.tokenABals[self.v] += st_token_amount
                            self.tokenABals[st_sender] -= st_token_amount
                        elif st_token == self.tokenB:
                            assert (
                                st_token.balanceOf(self.v.address)
                                == self.tokenBBals[self.v] + st_token_amount
                            )
                            self.tokenBBals[self.v] += st_token_amount
                            self.tokenBBals[st_sender] -= st_token_amount
                        else:
                            assert False, "Panicc"

                        assert tx.events["AddGasToken"][0].values() == [
                            hexStr(st_swapID),
                            st_token_amount,
                            st_token,
                        ]

        def rule_executexSwapAndCall_native(
            self,
            st_sender,
            st_dstAddress,
            st_native_amount,
            st_dstChain,
            st_message,
        ):
            assert self.cfReceiverMock.cfVault() == self.v.address
            signer = self._get_key_prob(AGG)

            # just to not create even more strategies
            st_srcAddress = st_dstAddress
            st_srcChain = st_dstChain

            message = hexStr(st_message)
            args = [
                [NATIVE_ADDR, self.cfReceiverMock.address, st_native_amount],
                st_srcChain,
                st_srcAddress,
                message,
            ]
            toLog = (*args, st_sender)
            if self.v_suspended:
                with reverts(REV_MSG_GOV_SUSPENDED):
                    print(
                        "        REV_MSG_GOV_SUSPENDED _executexSwapAndCall",
                    )
                    signed_call_km(
                        self.km,
                        self.v.executexSwapAndCall,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                if st_native_amount == 0:
                    print("        REV_MSG_NZ_UINT _executexSwapAndCall", *toLog)
                    with reverts(REV_MSG_NZ_UINT):
                        signed_call_km(
                            self.km,
                            self.v.executexSwapAndCall,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )
                elif not self.v in self.currentWhitelist:
                    print("        REV_MSG_WHITELIST rule_executexSwapAndCall", *toLog)
                    with reverts(REV_MSG_WHITELIST):
                        signed_call_km(
                            self.km,
                            self.v.executexSwapAndCall,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )

                elif signer != self.keyIDToCurKeys[AGG]:
                    print("        REV_MSG_SIG rule_executexSwapAndCall", signer)
                    with reverts(REV_MSG_SIG):
                        signed_call_km(
                            self.km,
                            self.v.executexSwapAndCall,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )

                else:
                    if web3.eth.get_balance(self.v.address) >= st_native_amount:
                        print("                    rule_executexSwapAndCall", *toLog)
                        tx = signed_call_km(
                            self.km,
                            self.v.executexSwapAndCall,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )
                        assert (
                            web3.eth.get_balance(self.v.address)
                            == self.nativeBals[self.v] - st_native_amount
                        )
                        self.nativeBals[self.v] -= st_native_amount
                        assert tx.events["ReceivedxSwapAndCall"][0].values() == [
                            st_srcChain,
                            hexStr(st_srcAddress),
                            message,
                            NATIVE_ADDR,
                            st_native_amount,
                            st_native_amount,
                        ]
                        self.lastValidateTime = tx.timestamp

        def rule_executexSwapAndCall_token(
            self,
            st_sender,
            st_dstAddress,
            st_token_amount,
            st_token,
            st_dstChain,
            st_message,
        ):
            signer = self._get_key_prob(AGG)

            # just to not create even more strategies
            st_srcAddress = st_dstAddress
            st_srcChain = st_dstChain

            message = hexStr(st_message)
            args = [
                [st_token, self.cfReceiverMock.address, st_token_amount],
                st_srcChain,
                st_srcAddress,
                message,
            ]
            toLog = (*args, st_sender)
            if self.v_suspended:
                with reverts(REV_MSG_GOV_SUSPENDED):
                    print("        REV_MSG_GOV_SUSPENDED _executexSwapAndCall")
                    signed_call_km(
                        self.km,
                        self.v.executexSwapAndCall,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                if st_token_amount == 0:
                    print("        REV_MSG_NZ_UINT _executexSwapAndCall", *toLog)
                    with reverts(REV_MSG_NZ_UINT):
                        signed_call_km(
                            self.km,
                            self.v.executexSwapAndCall,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )

                elif not self.v in self.currentWhitelist:
                    print("        REV_MSG_WHITELIST rule_executexSwapAndCall", *toLog)
                    with reverts(REV_MSG_WHITELIST):
                        signed_call_km(
                            self.km,
                            self.v.executexSwapAndCall,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )

                elif signer != self.keyIDToCurKeys[AGG]:
                    print("        REV_MSG_SIG rule_executexSwapAndCall", signer)
                    with reverts(REV_MSG_SIG):
                        signed_call_km(
                            self.km,
                            self.v.executexSwapAndCall,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )

                else:
                    if st_token.balanceOf(self.v.address) < st_token_amount:
                        print(
                            "        REV_MSG_ERC20_EXCEED_BAL _executexSwapAndCall",
                            *toLog,
                        )
                        with reverts(REV_MSG_ERC20_EXCEED_BAL):
                            signed_call_km(
                                self.km,
                                self.v.executexSwapAndCall,
                                *args,
                                signer=signer,
                                sender=st_sender,
                            )

                    else:
                        print("                    rule_executexSwapAndCall", *toLog)
                        tx = signed_call_km(
                            self.km,
                            self.v.executexSwapAndCall,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )

                        if st_token == self.tokenA:
                            assert (
                                st_token.balanceOf(self.v.address)
                                == self.tokenABals[self.v] - st_token_amount
                            )
                            self.tokenABals[self.v] -= st_token_amount
                        elif st_token == self.tokenB:
                            assert (
                                st_token.balanceOf(self.v.address)
                                == self.tokenBBals[self.v] - st_token_amount
                            )
                            self.tokenBBals[self.v] -= st_token_amount
                        else:
                            assert False, "Panicc"

                        assert tx.events["ReceivedxSwapAndCall"][0].values() == [
                            st_srcChain,
                            hexStr(st_srcAddress),
                            message,
                            st_token,
                            st_token_amount,
                            0,
                        ]
                        self.lastValidateTime = tx.timestamp

        def rule_executexCall(
            self,
            st_sender,
            st_dstAddress,
            st_dstChain,
            st_message,
        ):
            signer = self._get_key_prob(AGG)

            # just to not create even more strategies
            st_srcAddress = st_dstAddress
            st_srcChain = st_dstChain

            message = hexStr(st_message)
            args = [
                self.cfReceiverMock.address,
                st_srcChain,
                st_srcAddress,
                message,
            ]
            toLog = (*args, st_sender, signer)
            if self.v_suspended:
                with reverts(REV_MSG_GOV_SUSPENDED):
                    print(
                        "        REV_MSG_GOV_SUSPENDED _executexCall",
                    )
                    signed_call_km(
                        self.km, self.v.executexCall, *args, sender=st_sender
                    )
            elif not self.v in self.currentWhitelist:
                print("        REV_MSG_WHITELIST rule_executexCall", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km,
                        self.v.executexCall,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_executexCall", signer)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.v.executexCall,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                print("                    rule_executexCall", *toLog)
                tx = signed_call_km(
                    self.km, self.v.executexCall, *args, signer=signer, sender=st_sender
                )
                assert tx.events["ReceivedxCall"][0].values() == [
                    st_srcChain,
                    hexStr(st_srcAddress),
                    message,
                ]
                self.lastValidateTime = tx.timestamp

        # KeyManager

        # Dewhitelist all other addresses. Do this only rarely to prevent contracts not being functional too often
        def rule_updateCanConsumeKeyNonce_dewhitelist(
            self, st_sender, st_addr, st_addrs
        ):
            # So dewhitelisting only happens 1/5 of the times
            if st_addr != self.governor:
                return

            toWhitelist = st_addrs
            args = (self.currentWhitelist, toWhitelist)
            signer = self._get_key_prob(AGG)

            if signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_updateCanConsumeKeyNonce_dewhitelist")
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.km.updateCanConsumeKeyNonce,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                print(
                    "                    rule_updateCanConsumeKeyNonce_dewhitelist",
                    st_sender,
                )
                tx = signed_call_km(
                    self.km,
                    self.km.updateCanConsumeKeyNonce,
                    *args,
                    signer=signer,
                    sender=st_sender,
                )
                self.currentWhitelist = toWhitelist
                self.lastValidateTime = tx.timestamp

        # Updates the list of addresses that are nonce consumers. Dewhitelist other contracts
        def rule_updateCanConsumeKeyNonce_whitelist(self, st_sender):
            # Regardless of what is whitelisted, whitelist the current contracts
            toWhitelist = [self.v, self.sm, self.f] + list(a)
            args = (self.currentWhitelist, toWhitelist)
            signer = self._get_key_prob(AGG)

            if signer != self.keyIDToCurKeys[AGG]:
                print(
                    "        REV_MSG_SIG rule_updateCanConsumeKeyNonce_whitelist",
                    st_sender,
                )
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.km.updateCanConsumeKeyNonce,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                print(
                    "                    rule_updateCanConsumeKeyNonce_whitelist",
                    st_sender,
                )
                tx = signed_call_km(
                    self.km,
                    self.km.updateCanConsumeKeyNonce,
                    *args,
                    signer=signer,
                    sender=st_sender,
                )
                self.currentWhitelist = toWhitelist
                self.lastValidateTime = tx.timestamp

        # Get the key that is probably what we want, but also has a low chance of choosing
        # the 'wrong' key which will cause a revert and tests the full range. Maximises useful
        # results whilst still testing the full range.
        def _get_key_prob(self, keyID):
            samples = ([self.keyIDToCurKeys[keyID]] * 100) + self.allKeys
            return choice(samples)

        # Checks if consumeKeyNonce returns the correct value when called with a random sender,
        # signing key, random keyID that the signing key is supposed to be, and random msgData
        def rule_consumeKeyNonce(self, st_sender, st_sig_key_idx, st_msg_data):
            sigData = self.allKeys[st_sig_key_idx].getSigDataWithNonces(
                st_msg_data.hex(), nonces, self.km.address
            )
            toLog = (st_sender, st_sig_key_idx, st_msg_data)

            if not st_sender in self.currentWhitelist:
                print("        REV_MSG_WHITELIST rule_consumeKeyNonce", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    self.km.consumeKeyNonce(
                        sigData, cleanHexStr(sigData[2]), {"from": st_sender}
                    )
            elif self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[AGG]:
                print("                    rule_consumeKeyNonce", *toLog)
                tx = self.km.consumeKeyNonce(
                    sigData, cleanHexStr(sigData[2]), {"from": st_sender}
                )
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print("        REV_MSG_SIG rule_consumeKeyNonce", *toLog)
                    self.km.consumeKeyNonce(
                        sigData, cleanHexStr(sigData[2]), {"from": st_sender}
                    )

        # Replace a key with a setKeyWithAggKey call - used to update aggKey, govKey and commKey
        def _set_key_with_aggkey(
            self, st_sender, fcn, keyID, st_sig_key_idx, st_new_key_idx, newKey
        ):
            toLog = (st_sender, keyID, st_sig_key_idx, st_new_key_idx)
            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[keyID]:
                print(f"                    {fcn}", *toLog)
                return signed_call_km(
                    self.km,
                    fcn,
                    newKey,
                    signer=self.allKeys[st_sig_key_idx],
                    sender=st_sender,
                )
            else:
                with reverts(REV_MSG_SIG):
                    print(f"        REV_MSG_SIG {fcn}", *toLog)
                    signed_call_km(
                        self.km,
                        fcn,
                        newKey,
                        signer=self.allKeys[st_sig_key_idx],
                        sender=st_sender,
                    )
                return None

        # Call setAggKeyWithAggKey with a random new key, signing key, and sender
        def rule_setAggKeyWithAggKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            tx = self._set_key_with_aggkey(
                st_sender,
                self.km.setAggKeyWithAggKey,
                AGG,
                st_sig_key_idx,
                st_new_key_idx,
                self.allKeys[st_new_key_idx].getPubData(),
            )
            if tx is None:
                return

            self.keyIDToCurKeys[AGG] = self.allKeys[st_new_key_idx]
            self.lastValidateTime = tx.timestamp

        # Call rule_setGovKeyWithGovKey with a random new key, signing key, and sender
        def rule_setGovKeyWithGovKey(self, st_sender, st_addr):
            toLog = (st_sender, st_addr, self.communityKey)
            if st_sender == self.governor:
                print("                    rule_setGovKeyWithGovKey", *toLog)
                self.km.setGovKeyWithGovKey(st_addr, {"from": st_sender})
                self.governor = st_addr
            else:
                print(
                    "        REV_MSG_KEYMANAGER_GOVERNOR rule_setGovKeyWithGovKey",
                    *toLog,
                )
                with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
                    self.km.setGovKeyWithGovKey(st_addr, {"from": st_sender})

        # Useful results are being impeded by most attempts at setAggKeyWithGovKey not having enough
        # delay - having 2 sleep methods makes it more common aswell as this which is enough of a delay
        # in itself, since Hypothesis usually picks small values as part of shrinking
        def rule_sleep_2_days(self):
            print("                    rule_sleep_2_days")
            chain.sleep(2 * DAY)

        # Call setAggKeyWithGovKey with a random new key, signing key, and sender
        def rule_setAggKeyWithGovKey(self, st_sender, st_new_key_idx):

            sender = choice([st_sender, self.governor])
            toLog = (st_sender, sender, st_new_key_idx)

            if getChainTime() - self.lastValidateTime < AGG_KEY_TIMEOUT:
                print("        REV_MSG_DELAY rule_setAggKeyWithGovKey", *toLog)
                with reverts(REV_MSG_DELAY):
                    self.km.setAggKeyWithGovKey(
                        self.allKeys[st_new_key_idx].getPubData(),
                        {"from": sender},
                    )
            elif sender != self.governor:
                print("        REV_MSG_SIG rule_setAggKeyWithGovKey", *toLog)
                with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
                    self.km.setAggKeyWithGovKey(
                        self.allKeys[st_new_key_idx].getPubData(),
                        {"from": sender},
                    )
            else:
                print("                    rule_setAggKeyWithGovKey", *toLog)
                self.km.setAggKeyWithGovKey(
                    self.allKeys[st_new_key_idx].getPubData(),
                    {"from": sender},
                )

                self.keyIDToCurKeys[AGG] = self.allKeys[st_new_key_idx]

        # Call setGovKeyWithAggKey with a random new key, signing key, and sender
        def rule_setGovKeyWithAggKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            newGovKey = choice([st_sender, self.governor])

            tx = self._set_key_with_aggkey(
                st_sender,
                self.km.setGovKeyWithAggKey,
                AGG,
                st_sig_key_idx,
                st_new_key_idx,
                newGovKey,
            )
            if tx is None:
                return

            self.governor = newGovKey
            self.lastValidateTime = tx.timestamp

        # Call setGovKeyWithAggKey with a random new key, signing key, and sender
        def rule_setCommKeyWithAggKey(self, st_sender, st_sig_key_idx, st_new_key_idx):
            newCommKey = choice([st_sender, self.communityKey])

            tx = self._set_key_with_aggkey(
                st_sender,
                self.km.setCommKeyWithAggKey,
                AGG,
                st_sig_key_idx,
                st_new_key_idx,
                newCommKey,
            )
            if tx is None:
                return

            self.communityKey = newCommKey
            self.lastValidateTime = tx.timestamp

        # Updates community Key with a random new key - happens with low probability - 1/20
        def rule_setCommKeyWithCommKey(self, st_sender, st_addr):
            toLog = (st_sender, st_addr, self.communityKey)
            if st_sender == self.communityKey:
                print("                    rule_setCommKeyWithCommKey", *toLog)
                self.km.setCommKeyWithCommKey(st_addr, {"from": st_sender})
                self.communityKey = st_addr
            else:
                print(
                    "        REV_MSG_KEYMANAGER_NOT_COMMUNITY _setCommKeyWithCommKey",
                    *toLog,
                )
                with reverts(REV_MSG_KEYMANAGER_NOT_COMMUNITY):
                    self.km.setCommKeyWithCommKey(st_addr, {"from": st_sender})

        # StakeManager

        # Stakes a random amount from a random staker to a random nodeID
        def rule_stake(self, st_staker, st_nodeID, st_amount, st_returnAddr):
            args = (st_nodeID, st_amount, st_returnAddr)
            toLog = (*args, st_staker)
            if st_nodeID == 0:
                print("        REV_MSG_NZ_BYTES32 rule_stake", *toLog)
                with reverts(REV_MSG_NZ_BYTES32):
                    self.f.approve(self.sm.address, st_amount, {"from": st_staker})
                    self.sm.stake(
                        st_nodeID, st_amount, st_returnAddr, {"from": st_staker}
                    )
            elif st_amount < self.minStake:
                print("        rule_stake MIN_STAKE", *toLog)
                with reverts(REV_MSG_MIN_STAKE):
                    self.f.approve(self.sm.address, st_amount, {"from": st_staker})
                    self.sm.stake(
                        st_nodeID, st_amount, st_returnAddr, {"from": st_staker}
                    )
            elif st_amount > self.flipBals[st_staker]:
                print("        rule_stake REV_MSG_ERC20_EXCEED_BAL", *toLog)
                with reverts(REV_MSG_ERC20_EXCEED_BAL):
                    self.f.approve(self.sm.address, st_amount, {"from": st_staker})
                    self.sm.stake(
                        st_nodeID, st_amount, st_returnAddr, {"from": st_staker}
                    )
            else:
                print("                    rule_stake ", *toLog)
                self.f.approve(self.sm.address, st_amount, {"from": st_staker})
                self.sm.stake(st_nodeID, st_amount, st_returnAddr, {"from": st_staker})

                self.flipBals[st_staker] -= st_amount
                self.flipBals[self.sm] += st_amount
                self.totalStake += st_amount

        # Claims a random amount from a random nodeID to a random recipient
        def rule_registerClaim(
            self, st_nodeID, st_staker, st_amount, st_sender, st_expiry_time_diff
        ):
            args = (
                st_nodeID,
                st_amount,
                st_staker,
                getChainTime() + st_expiry_time_diff,
            )
            signer = self._get_key_prob(AGG)
            toLog = (*args, signer, st_sender)

            if self.sm_suspended:
                print("        REV_MSG_GOV_SUSPENDED _registerClaim")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif st_nodeID == 0:
                print("        NODEID rule_registerClaim", *toLog)
                with reverts(REV_MSG_NZ_BYTES32):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif st_amount == 0:
                print("        AMOUNT rule_registerClaim", *toLog)
                with reverts(REV_MSG_NZ_UINT):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif not self.sm in self.currentWhitelist:
                print("        REV_MSG_WHITELIST rule_registerClaim", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_registerClaim", signer)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif getChainTime() <= self.pendingClaims[st_nodeID][3]:
                print("        REV_MSG_CLAIM_EXISTS rule_registerClaim", *toLog)
                with reverts(REV_MSG_CLAIM_EXISTS):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif st_expiry_time_diff <= CLAIM_DELAY:
                print("        REV_MSG_EXPIRY_TOO_SOON rule_registerClaim", *toLog)
                with reverts(REV_MSG_EXPIRY_TOO_SOON):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                print("                    rule_registerClaim ", *toLog)
                tx = signed_call_km(
                    self.km,
                    self.sm.registerClaim,
                    *args,
                    signer=signer,
                    sender=st_sender,
                )
                self.pendingClaims[st_nodeID] = (
                    st_amount,
                    st_staker,
                    tx.timestamp + CLAIM_DELAY,
                    args[3],
                )
                self.lastValidateTime = tx.timestamp

        # Executes a random claim
        def rule_executeClaim(self, st_nodeID, st_sender):
            if self.sm_suspended:
                print("        REV_MSG_GOV_SUSPENDED _executeClaim")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.sm.executeClaim(st_nodeID, {"from": st_sender})
                return

            claim = self.pendingClaims[st_nodeID]

            if not claim[2] <= getChainTime():
                print("        REV_MSG_NOT_ON_TIME rule_executeClaim", st_nodeID)
                with reverts(REV_MSG_NOT_ON_TIME):
                    self.sm.executeClaim(st_nodeID, {"from": st_sender})
            # If it's expired it won't revert regardless of the token balances
            elif self.flipBals[self.sm] < claim[0] and not getChainTime() <= claim[3]:
                print("        REV_MSG_ERC20_EXCEED_BAL rule_executeClaim", st_nodeID)
                with reverts(REV_MSG_ERC20_EXCEED_BAL):
                    self.sm.executeClaim(st_nodeID, {"from": st_sender})
            else:
                print("                    rule_executeClaim", st_nodeID)
                tx = self.sm.executeClaim(st_nodeID, {"from": st_sender})

                # Claim expired
                if getChainTime() <= claim[3]:
                    assert tx.events["ClaimExpired"][0].values() == [
                        st_nodeID,
                        claim[1],
                    ]
                else:
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
                self.sm.setMinStake(st_minStake, {"from": st_sender})

                self.minStake = st_minStake

        # Tries to set the FLIP address. It should have been set right after the deployment.
        def rule_setFlip(self, st_sender, st_returnAddr):
            print("        REV_MSG_NZ_ADDR rule_setFlip", st_sender)
            with reverts(REV_MSG_NZ_ADDR):
                self.sm.setFlip(ZERO_ADDR, {"from": st_sender})

            print("        REV_MSG_FLIP_ADDRESS rule_setFlip", st_sender)
            with reverts(REV_MSG_FLIP_ADDRESS):
                self.sm.setFlip(st_returnAddr, {"from": st_sender})

        # FLIP

        # Updates Flip Supply minting/burning stakeManager tokens
        def rule_updateFlipSupply(self, st_sender, st_amount_supply, blockNumber_incr):

            sm_inibalance = self.f.balanceOf(self.sm)
            new_total_supply = self.f.totalSupply() + st_amount_supply

            # Avoid newSupplyBlockNumber being a negative number
            newSupplyBlockNumber = max(self.lastSupplyBlockNumber + blockNumber_incr, 0)

            args = (
                new_total_supply,
                newSupplyBlockNumber,
                self.sm.address,
            )
            signer = self._get_key_prob(AGG)
            toLog = (*args, signer, st_sender, st_amount_supply)

            if not self.f in self.currentWhitelist:
                print("        REV_MSG_WHITELIST rule_updateFlipSupply", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km,
                        self.f.updateFlipSupply,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_updateFlipSupply", *toLog)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.f.updateFlipSupply,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

            elif newSupplyBlockNumber <= self.lastSupplyBlockNumber:
                print("        REV_MSG_BLOCK rule_updateFlipSupply", *toLog)
                with reverts(REV_MSG_OLD_FLIP_SUPPLY_UPDATE):
                    signed_call_km(
                        self.km,
                        self.f.updateFlipSupply,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                if sm_inibalance + st_amount_supply < 0:
                    with reverts(REV_MSG_BURN_BALANCE):
                        print(
                            "        REV_MSG_BURN_BALANCE rule_updateFlipSupply", *toLog
                        )
                        signed_call_km(
                            self.km,
                            self.f.updateFlipSupply,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )
                else:
                    print("                    rule_updateFlipSupply", *toLog)
                    tx = signed_call_km(
                        self.km,
                        self.f.updateFlipSupply,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

                    assert self.f.totalSupply() == new_total_supply
                    assert self.f.balanceOf(self.sm) == sm_inibalance + st_amount_supply

                    self.flipBals[self.sm] += st_amount_supply
                    self.lastSupplyBlockNumber = newSupplyBlockNumber
                    self.lastValidateTime = tx.timestamp

        # AggKeyNonceConsumer - upgradability

        # Deploys a new keyManager and updates all the references to it
        def rule_upgrade_keyManager(self, st_sender):
            aggKeyNonceConsumers = [self.f, self.sm, self.v]

            # Reusing current keyManager aggregateKey for simplicity.
            newKeyManager = st_sender.deploy(
                KeyManager, self.km.getAggregateKey(), self.governor, self.communityKey
            )
            toWhitelist = self.currentWhitelist.copy()

            # If we deploy an upgraded KeyManager we can probably have setCanConsumeKeyNonce
            # as part of the constructor, so we don't need to call it here.
            newKeyManager.setCanConsumeKeyNonce(toWhitelist, {"from": st_sender})

            signer = self._get_key_prob(AGG)

            # If any nonceConsumer is not whitelisted in oldKeyManager, check and return
            for aggKeyNonceConsumer in aggKeyNonceConsumers:
                if not aggKeyNonceConsumer in self.currentWhitelist:
                    assert self.km.canConsumeKeyNonce(aggKeyNonceConsumer) == False
                    with reverts(REV_MSG_WHITELIST):
                        print(
                            "        REV_MSG_WHITELIST rule_upgrade_keyManager",
                            st_sender,
                            newKeyManager.address,
                        )
                        signed_call_km(
                            self.km,
                            aggKeyNonceConsumer.updateKeyManager,
                            newKeyManager,
                            signer=signer,
                            sender=st_sender,
                        )
                    return

            # All whitelisted
            if signer != self.keyIDToCurKeys[AGG]:
                print(
                    "        REV_MSG_SIG rule_upgrade_keyManager",
                    st_sender,
                    newKeyManager.address,
                )
                # Use the first aggKeyNonceConsumer for simplicity
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        aggKeyNonceConsumers[0].updateKeyManager,
                        newKeyManager,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                print(
                    "                    rule_upgrade_keyManager",
                    st_sender,
                    newKeyManager.address,
                )

                for aggKeyNonceConsumer in aggKeyNonceConsumers:
                    assert aggKeyNonceConsumer.getKeyManager() == self.km
                    signed_call_km(
                        self.km,
                        aggKeyNonceConsumer.updateKeyManager,
                        newKeyManager,
                        signer=signer,
                        sender=st_sender,
                    )
                    assert aggKeyNonceConsumer.getKeyManager() == newKeyManager

                self._updateBalancesOnUpgrade(self.km, newKeyManager)
                self.km = newKeyManager
                self.lastValidateTime = self.km.tx.timestamp
                self.currentWhitelist = toWhitelist

        # Deploys a new Vault and transfers the funds from the old Vault to the new one
        def rule_upgrade_Vault(self, st_sender, st_native_amount, st_sleep_time):
            newVault = st_sender.deploy(Vault, self.km)

            # Keep old Vault whitelisted
            toWhitelist = self.currentWhitelist.copy() + [newVault]
            args = [
                [
                    NATIVE_ADDR,
                    st_sender,
                    st_native_amount,
                ]
            ]
            signer = self._get_key_prob(AGG)
            toLog = (*args, st_sender)
            if self.v_suspended:
                print("        REV_MSG_GOV_SUSPENDED rule_upgrade_Vault")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km, self.v.transfer, *args, signer=signer, sender=st_sender
                    )
            # if old vault is not whitelisted it will fail later
            elif not self.v in self.currentWhitelist:
                print("        REV_MSG_WHITELIST rule_upgrade_Vault", *toLog)
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km, self.v.transfer, *args, signer=signer, sender=st_sender
                    )
            else:
                args = (self.currentWhitelist, toWhitelist)

                if signer != self.keyIDToCurKeys[AGG]:
                    print("        REV_MSG_SIG rule_upgrade_Vault", *toLog)
                    with reverts(REV_MSG_SIG):
                        signed_call_km(
                            self.km,
                            self.km.updateCanConsumeKeyNonce,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )
                else:
                    # UpdateCanConsumeKeyNonce
                    signed_call_km(
                        self.km,
                        self.km.updateCanConsumeKeyNonce,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
                    self.currentWhitelist = toWhitelist.copy()

                    chain.sleep(st_sleep_time)

                    # Transfer all the remaining native and other funds (TokenA & TokenB) to new Vault and dewhitelist
                    iniNativeBalance = self.v.balance()
                    initTokenABalance = self.tokenA.balanceOf(self.v)
                    iniTokenBBalance = self.tokenB.balanceOf(self.v)

                    amountsToTransfer = [
                        iniNativeBalance,
                        initTokenABalance,
                        iniTokenBBalance,
                    ]

                    print("                    rule_upgrade_vault", *amountsToTransfer)

                    tokens = [NATIVE_ADDR, self.tokenA, self.tokenB]
                    recipients = [newVault, newVault, newVault]

                    args = [
                        craftTransferParamsArray(tokens, recipients, amountsToTransfer)
                    ]

                    signed_call_km(
                        self.km,
                        self.v.transferBatch,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

                    # Check that all balances have been transferred
                    assert self.v.balance() == 0
                    assert self.tokenA.balanceOf(self.v) == 0
                    assert self.tokenB.balanceOf(self.v) == 0

                    assert self.tokenA.balanceOf(newVault) == initTokenABalance
                    assert self.tokenB.balanceOf(newVault) == iniTokenBBalance

                    self._updateBalancesOnUpgrade(self.v, newVault)

                    # Dewhitelist old Vault
                    toWhitelist = self.currentWhitelist.copy()
                    toWhitelist.remove(self.v)

                    # UpdateCanConsumeKeyNonce
                    args = (
                        self.currentWhitelist,
                        toWhitelist,
                    )
                    tx = signed_call_km(
                        self.km,
                        self.km.updateCanConsumeKeyNonce,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

                    # Update state variables
                    self.v = newVault
                    self.lastValidateTime = tx.timestamp
                    self.currentWhitelist = toWhitelist
                    self.v_communityGuardDisabled = False
                    self.communityKey = self.communityKey
                    self.v_suspended = False

                    # Deploy a new CFReceiverMock that receives from the new Vault
                    self.cfReceiverMock = st_sender.deploy(CFReceiverMock, self.v)

                    # Create new addresses for the new Vault and initialize Balances
                    newCreate2EthAddrs = [
                        getCreate2Addr(
                            self.v.address,
                            cleanHexStrPad(swapID),
                            Deposit,
                            cleanHexStrPad(NATIVE_ADDR),
                        )
                        for swapID in range(MAX_SWAPID + 1)
                    ]
                    newCreate2TokenAAddrs = [
                        getCreate2Addr(
                            self.v.address,
                            cleanHexStrPad(swapID),
                            Deposit,
                            cleanHexStrPad(self.tokenA.address),
                        )
                        for swapID in range(MAX_SWAPID + 1)
                    ]
                    newCreate2TokenBAddrs = [
                        getCreate2Addr(
                            self.v.address,
                            cleanHexStrPad(swapID),
                            Deposit,
                            cleanHexStrPad(self.tokenB.address),
                        )
                        for swapID in range(MAX_SWAPID + 1)
                    ]

                    for swapID in range(MAX_SWAPID + 1):
                        # No need to update balances but we need to add new addresses to the self.Address list and the bals dictionary
                        self._addNewAddress(newCreate2EthAddrs[swapID])
                        self._addNewAddress(newCreate2TokenAAddrs[swapID])
                        self._addNewAddress(newCreate2TokenBAddrs[swapID])

                    self.deployedDeposits = dict()

        # Deploys a new Stake Manager and transfers the FLIP tokens from the old SM to the new one
        def rule_upgrade_stakeManager(self, st_sender, st_sleep_time):
            newStakeManager = st_sender.deploy(StakeManager, self.km, INIT_MIN_STAKE)

            # In case of deploying a new StakeManager, the setFLIP function will probably be part of
            # the constructor to avoid frontrunning, as there is no deployer check now.
            newStakeManager.setFlip(self.f, {"from": st_sender})

            # Keep old StakeManager whitelisted
            toWhitelist = self.currentWhitelist.copy() + [newStakeManager]
            args = (JUNK_HEX, 1, newStakeManager, 1)
            signer = self._get_key_prob(AGG)
            toLog = (*args, st_sender)

            if self.sm_suspended:
                print("        REV_MSG_GOV_SUSPENDED rule_upgrade_stakeManager")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            # If old stakeManager is not whitelisted it will revert later on
            elif not self.sm in self.currentWhitelist:
                print(
                    "        REV_MSG_WHITELIST rule_upgrade_stakeManager",
                    *toLog,
                )
                with reverts(REV_MSG_WHITELIST):
                    signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                args = (
                    self.currentWhitelist,
                    toWhitelist,
                )
                if signer != self.keyIDToCurKeys[AGG]:
                    print(
                        "        REV_MSG_SIG rule_upgrade_stakeManager",
                        *toLog,
                    )
                    with reverts(REV_MSG_SIG):
                        signed_call_km(
                            self.km,
                            self.km.updateCanConsumeKeyNonce,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )
                else:
                    signed_call_km(
                        self.km,
                        self.km.updateCanConsumeKeyNonce,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
                    self.currentWhitelist = toWhitelist.copy()

                    chain.sleep(st_sleep_time)

                    # Generate claim to move all FLIP to new stakeManager
                    expiryTime = getChainTime() + (CLAIM_DELAY * 10)
                    claimAmount = self.flipBals[self.sm]
                    # Register Claim to transfer all flip
                    args = (
                        JUNK_HEX,
                        claimAmount,
                        newStakeManager,
                        expiryTime,
                    )
                    tx = signed_call_km(
                        self.km,
                        self.sm.registerClaim,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

                    chain.sleep(st_sleep_time)
                    if st_sleep_time < CLAIM_DELAY:
                        with reverts(REV_MSG_NOT_ON_TIME):
                            print(
                                "        REV_MSG_SIG rule_upgrade_stakeManager",
                                st_sleep_time,
                            )
                            self.sm.executeClaim(JUNK_HEX, {"from": st_sender})

                    chain.sleep(CLAIM_DELAY * 2)

                    print(
                        "                   rule_executeClaim", newStakeManager.address
                    )
                    assert self.f.balanceOf(newStakeManager) == 0
                    assert self.f.balanceOf(self.sm) == self.flipBals[self.sm]

                    self.sm.executeClaim(JUNK_HEX, {"from": st_sender})

                    assert self.f.balanceOf(newStakeManager) == self.flipBals[self.sm]
                    assert self.f.balanceOf(self.sm) == 0

                    # Dewhitelist old StakeManager
                    toWhitelist = self.currentWhitelist.copy()
                    toWhitelist.remove(self.sm)

                    # UpdateCanConsumeKeyNonce
                    args = (
                        self.currentWhitelist,
                        toWhitelist,
                    )
                    tx = signed_call_km(
                        self.km,
                        self.km.updateCanConsumeKeyNonce,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

                    self._updateBalancesOnUpgrade(self.sm, newStakeManager)
                    self.sm = newStakeManager
                    self.minStake = INIT_MIN_STAKE
                    self.lastValidateTime = tx.timestamp
                    self.currentWhitelist = toWhitelist
                    self.sm_communityGuardDisabled = False
                    self.communityKey = self.communityKey
                    self.sm_suspended = False

                    # Reset all pending claims
                    self.pendingClaims = {
                        nodeID: NULL_CLAIM for nodeID in range(MAX_NUM_SENDERS + 1)
                    }

        # Governance Community Guarded

        # Suspends the stake Manager if st_sender matches the governor address.
        def rule_suspend_stakeManager(self, st_sender, st_addr):
            if st_sender == self.governor:
                # To avoid suspending it very often
                if st_addr != st_sender:
                    return
                if self.sm_suspended:
                    print("        REV_MSG_GOV_SUSPENDED _suspend")
                    with reverts(REV_MSG_GOV_SUSPENDED):
                        self.sm.suspend({"from": st_sender})
                else:
                    print("                    rule_suspend", st_sender)
                    self.sm.suspend({"from": st_sender})
                    self.sm_suspended = True
            else:
                print("        REV_MSG_GOV_GOVERNOR _suspend")
                with reverts(REV_MSG_GOV_GOVERNOR):
                    self.sm.suspend({"from": st_sender})

        # Resumes the stake Manager if it is suspended. We always resume it to avoid
        # having the stakeManager suspended too often
        def rule_resume_stakeManager(self, st_sender):
            if self.sm_suspended:
                if st_sender != self.governor:
                    with reverts(REV_MSG_GOV_GOVERNOR):
                        self.sm.resume({"from": st_sender})
                # Always resume
                print("                    rule_resume", st_sender)
                self.sm.resume({"from": self.governor})
                self.sm_suspended = False
            else:
                print("        REV_MSG_GOV_NOT_SUSPENDED _resume", st_sender)
                with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                    self.sm.resume({"from": self.governor})

        # Suspends the stake Manager if st_sender matches the governor address.
        def rule_suspend_vault(self, st_sender, st_addr):
            if st_sender == self.governor:
                # To avoid suspending it very often
                if st_addr != st_sender:
                    return
                if self.v_suspended:
                    print("        REV_MSG_GOV_SUSPENDED _suspend")
                    with reverts(REV_MSG_GOV_SUSPENDED):
                        self.v.suspend({"from": st_sender})
                else:
                    print("                    rule_suspend", st_sender)
                    self.v.suspend({"from": st_sender})
                    self.v_suspended = True
            else:
                print("        REV_MSG_GOV_GOVERNOR _suspend")
                with reverts(REV_MSG_GOV_GOVERNOR):
                    self.v.suspend({"from": st_sender})

        # Resumes the stake Manager if it is suspended. We always resume it to avoid
        # having the stakeManager suspended too often
        def rule_resume_vault(self, st_sender):
            if self.v_suspended:
                if st_sender != self.governor:
                    with reverts(REV_MSG_GOV_GOVERNOR):
                        self.v.resume({"from": st_sender})
                # Always resume
                print("                    rule_resume", st_sender)
                self.v.resume({"from": self.governor})
                self.v_suspended = False
            else:
                print("        REV_MSG_GOV_NOT_SUSPENDED _resume", st_sender)
                with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                    self.v.resume({"from": self.governor})

        # Enable Stake Manager's community Guard
        def rule_sm_enableCommunityGuard(self, st_sender):
            if self.sm_communityGuardDisabled:
                if st_sender != self.communityKey:
                    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                        self.sm.enableCommunityGuard({"from": st_sender})
                # Always enable
                print("                    rule_sm_enableCommunityGuard", st_sender)
                self.sm.enableCommunityGuard({"from": self.communityKey})
                self.sm_communityGuardDisabled = False
            else:
                print(
                    "        REV_MSG_GOV_ENABLED_GUARD _sm_enableCommunityGuard",
                    st_sender,
                )
                with reverts(REV_MSG_GOV_ENABLED_GUARD):
                    self.sm.enableCommunityGuard({"from": self.communityKey})

        # Disable Stake Manager's community Guard
        def rule_sm_disableCommunityGuard(self, st_sender):
            if not self.sm_communityGuardDisabled:
                if st_sender != self.communityKey:
                    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                        self.sm.disableCommunityGuard({"from": st_sender})
                # Always disable
                print("                    rule_sm_disableCommunityGuard", st_sender)
                self.sm.disableCommunityGuard({"from": self.communityKey})
                self.sm_communityGuardDisabled = True
            else:
                print(
                    "        REV_MSG_GOV_DISABLED_GUARD _sm_disableCommunityGuard",
                    st_sender,
                )
                with reverts(REV_MSG_GOV_DISABLED_GUARD):
                    self.sm.disableCommunityGuard({"from": self.communityKey})

        # Enable Vault's community Guard
        def rule_vault_enableCommunityGuard(self, st_sender):
            if self.v_communityGuardDisabled:
                if st_sender != self.communityKey:
                    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                        self.v.enableCommunityGuard({"from": st_sender})
                # Always enable
                print("                    rule_v_enableCommunityGuard", st_sender)
                self.v.enableCommunityGuard({"from": self.communityKey})
                self.v_communityGuardDisabled = False
            else:
                print(
                    "        REV_MSG_GOV_ENABLED_GUARD _v_enableCommunityGuard",
                    st_sender,
                )
                with reverts(REV_MSG_GOV_ENABLED_GUARD):
                    self.v.enableCommunityGuard({"from": self.communityKey})

        # Disable Vault's community Guard
        def rule_vault_disableCommunityGuard(self, st_sender):
            if not self.v_communityGuardDisabled:
                if st_sender != self.communityKey:
                    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                        self.v.disableCommunityGuard({"from": st_sender})
                # Always disable
                print("                    rule_v_disableCommunityGuard", st_sender)
                self.v.disableCommunityGuard({"from": self.communityKey})
                self.v_communityGuardDisabled = True
            else:
                print(
                    "        REV_MSG_GOV_DISABLED_GUARD _v_disableCommunityGuard",
                    st_sender,
                )
                with reverts(REV_MSG_GOV_DISABLED_GUARD):
                    self.v.disableCommunityGuard({"from": self.communityKey})

        # Governance attemps to withdraw FLIP from the Stake Manager in case of emergency
        def rule_sm_govWithdrawal(self, st_sender):
            if self.sm_communityGuardDisabled:
                if st_sender != self.governor:
                    with reverts(REV_MSG_GOV_GOVERNOR):
                        self.sm.govWithdraw({"from": st_sender})

                if self.sm_suspended:
                    print("                    rule_govWithdrawal", st_sender)
                    self.sm.govWithdraw({"from": self.governor})
                    # Governor has all the FLIP - do the checking and return the tokens for the invariant check
                    assert (
                        self.f.balanceOf(self.governor)
                        == self.flipBals[self.governor] + self.flipBals[self.sm]
                    )
                    assert self.f.balanceOf(self.sm) == 0
                    self.f.transfer(
                        self.sm, self.flipBals[self.sm], {"from": self.governor}
                    )
                else:
                    print("        REV_MSG_GOV_NOT_SUSPENDED _govWithdrawal")
                    with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                        self.sm.govWithdraw({"from": self.governor})
            else:
                print("        REV_MSG_GOV_ENABLED_GUARD _govWithdrawal")
                with reverts(REV_MSG_GOV_ENABLED_GUARD):
                    self.sm.govWithdraw({"from": self.governor})

        # Governance attemps to withdraw all tokens from the Vault in case of emergency
        def rule_v_govWithdrawal(self, st_sender):
            # Withdraw token A and token B - not native to make the checking easier due to gas expenditure
            tokenstoWithdraw = self.tokensList[1:]
            if self.v_communityGuardDisabled:
                if st_sender != self.governor:
                    with reverts(REV_MSG_GOV_GOVERNOR):
                        self.v.govWithdraw(tokenstoWithdraw, {"from": st_sender})

                if self.v_suspended:
                    if (
                        getChainTime() - self.km.getLastValidateTime()
                        < AGG_KEY_EMERGENCY_TIMEOUT
                    ):
                        print("        REV_MSG_VAULT_DELAY _govWithdrawal")
                        with reverts(REV_MSG_VAULT_DELAY):
                            self.v.govWithdraw(
                                tokenstoWithdraw, {"from": self.governor}
                            )
                    else:
                        # tokenstoWithdraw contains tokenA and tokenB
                        print("                    rule_govWithdrawal", st_sender)
                        self.v.govWithdraw(tokenstoWithdraw, {"from": self.governor})
                        # Governor has all the tokens - do the checking and return the tokens for the invariant check
                        assert (
                            tokenstoWithdraw[0].balanceOf(self.governor)
                            == self.tokenABals[self.governor] + self.tokenABals[self.v]
                        )
                        assert tokenstoWithdraw[0].balanceOf(self.v) == 0
                        tokenstoWithdraw[0].transfer(
                            self.v, self.tokenABals[self.v], {"from": self.governor}
                        )
                        assert (
                            tokenstoWithdraw[1].balanceOf(self.governor)
                            == self.tokenBBals[self.governor] + self.tokenBBals[self.v]
                        )
                        assert tokenstoWithdraw[1].balanceOf(self.v) == 0
                        tokenstoWithdraw[1].transfer(
                            self.v, self.tokenBBals[self.v], {"from": self.governor}
                        )

                else:
                    print("        REV_MSG_GOV_NOT_SUSPENDED _govWithdrawal")
                    with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                        self.v.govWithdraw(tokenstoWithdraw, {"from": self.governor})
            else:
                print("        REV_MSG_GOV_ENABLED_GUARD _govWithdrawal")
                with reverts(REV_MSG_GOV_ENABLED_GUARD):
                    self.v.govWithdraw(tokenstoWithdraw, {"from": self.governor})

        # Transfer native to the stakeManager to check govWithdrawalNative. Using st_staker to make sure it is a key in the nativeBals dict
        def _transfer_native_sm(self, st_staker, st_native_amount):
            self._transfer_native(st_staker, self.sm, st_native_amount)

        # Transfer native to the stakeManager to check govWithdrawalNative. Using st_staker to make sure it is a key in the nativeBals dict
        def _transfer_native_km(self, st_staker, st_native_amount):
            self._transfer_native(st_staker, self.km, st_native_amount)

        # Transfer native from sender to receiver. Both need be keys in the nativeBals dict
        def _transfer_native(self, sender, receiver, amount):
            if self.nativeBals[sender] >= amount:
                print(
                    "                    rule_transfer_native", sender, receiver, amount
                )
                sender.transfer(receiver, amount)
                self.nativeBals[sender] -= amount
                self.nativeBals[receiver] += amount

        # Governance attemps to withdraw StakeManager's NATIVE
        def rule_govWithdrawalNative_sm(self):
            self._govWithdrawalNative(self.sm)

        # Governance attemps to withdraw KeyManager's NATIVE
        def rule_govWithdrawalNative_km(self):
            self._govWithdrawalNative(self.km)

        # Governance attemps to withdraw contract's native- final balances will be check by the invariants
        def _govWithdrawalNative(self, contract):
            print("                    rule_govWithdrawalNative")
            contract.govWithdrawNative({"from": self.governor})
            self.nativeBals[self.governor] += self.nativeBals[contract]
            self.nativeBals[contract] = 0

        def rule_govAction(self, st_sender, st_message_govAction):
            if st_sender != self.governor:
                with reverts(REV_MSG_KEYMANAGER_GOVERNOR):
                    self.km.govAction(JUNK_HEX, {"from": st_sender})
            print("                    rule_govAction")
            tx = self.km.govAction(st_message_govAction, {"from": self.governor})
            assert tx.events["GovernanceAction"]["message"] == "0x" + cleanHexStr(
                st_message_govAction
            )

        # Check all the balances of every address are as they should be after every tx
        # If the contracts have been upgraded, the latest one should hold all the balance
        # NOTE: Error in self.nativeBals assertion - calculateGasSpentByAddress seems to be smaller than expected and intermittently the native balance
        # assertion fails. Could be that the tx gas values are off or that brownie and/or history.filter has a bug and doesn't report all the
        # sent transactions. It's an error that only occurs at the end of a test, so it is unlikely that the calculations are wrong or that
        # we need to add the wait_for_transaction_receipt before doing the calculation. Adding a time.sleep(3) seems to make all runs pass.
        # Another solution is to remove the assertion (not ideal) or to use the pytest approximation, though I've seen an old error appear
        # when doing that (end-of-run revert error that I thought was solved by spinning the node externally)
        def invariant_bals(self):
            self.numTxsTested += 1
            time.sleep(3)
            for addr in self.allAddrs:
                assert web3.eth.get_balance(str(addr)) == self.nativeBals[
                    addr
                ] - calculateGasSpentByAddress(addr, self.iniTransactionNumber[addr])
                assert self.tokenA.balanceOf(addr) == self.tokenABals[addr]
                assert self.tokenB.balanceOf(addr) == self.tokenBBals[addr]
                assert self.f.balanceOf(addr) == self.flipBals[addr]

        # Regardless of contract redeployment check that references are correct
        def invariant_addresses(self):
            assert (
                self.km.address
                == self.v.getKeyManager()
                == self.sm.getKeyManager()
                == self.f.getKeyManager()
            )

            assert self.sm.getFLIP() == self.f.address

        def invariant_whitelist(self):
            assert self.km.getNumberWhitelistedAddresses() == len(self.currentWhitelist)
            for address in self.currentWhitelist:
                assert self.km.canConsumeKeyNonce(address) == True

        # Check the keys are correct after every tx
        def invariant_keys(self):
            assert (
                self.km.getAggregateKey() == self.keyIDToCurKeys[AGG].getPubDataWith0x()
            )
            assert (
                self.governor
                == self.km.getGovernanceKey()
                == self.sm.getGovernor()
                == self.v.getGovernor()
            )
            assert (
                self.communityKey
                == self.km.getCommunityKey()
                == self.sm.getCommunityKey()
                == self.v.getCommunityKey()
            )

        # Check the state variables after every tx
        def invariant_state_vars(self):
            assert self.f.getLastSupplyUpdateBlockNumber() == self.lastSupplyBlockNumber
            assert self.sm.getMinimumStake() == self.minStake
            assert self.sm_communityGuardDisabled == self.sm.getCommunityGuardDisabled()
            assert self.sm_suspended == self.sm.getSuspendedState()
            assert self.v_communityGuardDisabled == self.v.getCommunityGuardDisabled()
            assert self.v_suspended == self.v.getSuspendedState()
            assert self.km.getLastValidateTime() == self.lastValidateTime
            for nodeID, claim in self.pendingClaims.items():
                assert self.sm.getPendingClaim(nodeID) == claim
            ## Check that there are contracts in the deposit Addresses
            for addr in self.deployedDeposits.values():
                assert web3.eth.get_code(web3.toChecksumAddress(addr)).hex() != "0x"

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f"Total rules executed = {self.numTxsTested-1}")

        # Update balances when a contract has been upgraded
        def _updateBalancesOnUpgrade(self, oldContract, newContract):
            self._addNewAddress(newContract)

            self.nativeBals[newContract] = self.nativeBals[oldContract]
            self.nativeBals[oldContract] = 0

            self.tokenABals[newContract] = self.tokenABals[oldContract]
            self.tokenABals[oldContract] = 0

            self.tokenBBals[newContract] = self.tokenBBals[oldContract]
            self.tokenBBals[oldContract] = 0

            self.flipBals[newContract] = self.flipBals[oldContract]
            self.flipBals[oldContract] = 0

        # Update balances when a contract has been upgraded
        def _addNewAddress(self, newAddress):
            self.allAddrs += [newAddress]
            # Initialize Key - no need to take account gas expenditure in newly deployed addresses since we only perform transactions from accounts within "a"
            self.iniTransactionNumber[newAddress] = 0
            # Initialize balances
            self.nativeBals[newAddress] = 0
            self.tokenABals[newAddress] = 0
            self.tokenBBals[newAddress] = 0
            self.flipBals[newAddress] = 0

    state_machine(
        StateMachine,
        a,
        cfDeployAllWhitelist,
        Deposit,
        Token,
        CFReceiverMock,
        settings=settings,
    )
