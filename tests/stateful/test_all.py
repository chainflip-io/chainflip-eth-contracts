from consts import *
from shared_tests import *
from brownie import reverts, chain, web3
from brownie.test import strategy, contract_strategy
from brownie.convert import to_bytes
from utils import *
from hypothesis import strategies as hypStrat
from random import choice, choices
import time
from deploy import deploy_new_stateChainGateway, deploy_new_vault, deploy_new_keyManager

settings = {
    "stateful_step_count": 100,
    "max_examples": 50,
}

# Stateful test for all functions in the Vault, KeyManager, and StateChainGateway
def test_all(
    BaseStateMachine,
    state_machine,
    a,
    cfDeploy,
    Deposit,
    Token,
    StateChainGateway,
    KeyManager,
    Vault,
    CFReceiverMock,
    MockUSDT,
    FLIP,
    DeployerStateChainGateway,
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

    # StateChainGateway
    INIT_FUNDING = 10**25
    # Setting this low because Brownie/Hypothesis 'shrinks' random
    # numbers so that they cluster near the minimum, and we want to maximise
    # the amount of non-reverted txs there are, while also allowing for some reverts
    INIT_MIN_FUNDING = 1000
    MAX_TEST_FUND = 10**6 * E_18
    INIT_FLIP_SM = 25 * 10**4 * E_18

    SUPPLY_BLOCK_NUMBER_RANGE = 10

    class StateMachine(BaseStateMachine):

        # Max funds in the Vault
        TOTAL_FUNDS = 10**3 * E_18

        """
        This test calls functions Vault, from KeyManager and StateChainGateway in random orders.

        It uses a set number of Deposit contracts/create2 addresses
        for native & each token (MAX_SWAPID amount of each, 3 * MAX_SWAPID total) and also
        randomly sends native and the 2 ERC20 tokens to the create2 addresses that
        correspond to the create2 addresses so that something can actually be fetched
        and transferred.

        Keys are attempted to be set as random keys with a random signing key - all
        keys are from a pool of the default AGG_KEY and GOV_KEY plus freshly generated
        keys at the start of each run.

        There's a MAX_NUM_SENDERS number of funders that randomly `fund` and are randomly
        the recipients of `redemption`. The parameters used are so that they're.scgall enough
        to increase the likelihood of the same address being used in multiple
        interactions (e.g. 2  x fundings then a redemption etc) and large enough to ensure
        there's variety in them.

        The parameters used are so that they're.scgall enough to increase the likelihood of the same
        address being used in multiple interactions and large enough to ensure there's variety in them
        
        This test also deploys a new version of the following contracts: StateChainGateway, Vault and KeyManager

        All the references to these contracts need to be updated in the already deployed contracts.
        """

        # Set up the initial test conditions once
        def __init__(cls, a, cfDeploy, Deposit, Token, CFReceiverMock, MockUSDT):
            super().__init__(cls, a, cfDeploy)

            cls.tokenA = a[0].deploy(
                Token, "NotAPonziA", "NAPA", INIT_TOKEN_SUPPLY * 10
            )
            cls.tokenB = a[0].deploy(
                MockUSDT, "NotAPonziB", "NAPB", INIT_TOKEN_SUPPLY * 10
            )
            cls.tokensList = (NATIVE_ADDR, cls.tokenA, cls.tokenB)

            for token in [cls.tokenA, cls.tokenB]:
                for recip in a[1:]:
                    token.transfer(recip, INIT_TOKEN_AMNT)
                # Send excess from the deployer to the zero address so that all funders start
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

            cls.funders = a[:MAX_NUM_SENDERS]

            for funder in cls.funders:
                cls.f.transfer(funder, INIT_FUNDING, {"from": a[0]})
            # Send excess from the deployer to the zero address so that all funders start
            # with the same balance to make the accounting simpler
            cls.f.transfer(
                "0x0000000000000000000000000000000000000001",
                cls.f.balanceOf(a[0]) - INIT_FUNDING,
                {"from": a[0]},
            )

            # Vault - initialize with some funds
            a[3].transfer(cls.v, cls.TOTAL_FUNDS)

            # Workaround for initial contract's Balances
            initialVaultBalance = web3.eth.get_balance(cls.v.address)
            assert initialVaultBalance == cls.TOTAL_FUNDS
            initialKeyManagerBalance = web3.eth.get_balance(cls.km.address)
            initialStateChainGatewayBalance = web3.eth.get_balance(cls.scg.address)
            cls.initialBalancesContracts = [
                initialVaultBalance,
                initialKeyManagerBalance,
                initialStateChainGatewayBalance,
            ]

            # Store original contracts to be able to test upgradability
            cls.orig_scg = cls.scg
            cls.orig_v = cls.v
            cls.orig_km = cls.km

            # Deploy a CFReceiverMock
            cls.cfReceiverMock = a[0].deploy(CFReceiverMock, cls.v.address)
            cls.orig_cfRec = cls.cfReceiverMock

            assert cls.cfReceiverMock.cfVault() == cls.v.address

        # Reset the local versions of state to compare the contract to after every run
        def setup(self):

            # Set original contracts to be able to test upgradability
            self.scg = self.orig_scg
            self.v = self.orig_v
            self.km = self.orig_km
            self.cfReceiverMock = self.orig_cfRec

            self.governor = cfDeploy.gov
            self.communityKey = cfDeploy.communityKey

            self.allAddrs = self.funders
            self.allAddrs = [
                *[addr.address for addr in self.funders],
                *self.create2EthAddrs,
                *self.create2TokenAAddrs,
                *self.create2TokenBAddrs,
            ]

            self.scg.setMinFunding(INIT_MIN_FUNDING, {"from": self.governor})

            self.nativeBals = {
                # Accounts within "a" will have INIT_NATIVE_BAL - gas spent in setup/deployment
                addr: web3.eth.get_balance(str(addr)) if addr in a else 0
                for addr in self.allAddrs
            }

            # Set intial balances of remaining contracts
            contracts = [self.v, self.km, self.scg]
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
            self.lastValidateTime = self.deployerContract.tx.timestamp
            self.keyIDToCurKeys = {AGG: AGG_SIGNER_1}
            self.allKeys = [*self.keyIDToCurKeys.values()] + (
                [Signer.gen_signer(None, {})]
                * (TOTAL_KEYS - len(self.keyIDToCurKeys.values()))
            )

            # StateChainGateway
            self.totalFunding = 0
            self.minFunding = INIT_MIN_FUNDING
            self.flipBals = {
                addr: INIT_FUNDING
                if addr in self.funders
                else (INIT_FLIP_SM if addr == self.scg else 0)
                for addr in self.allAddrs
            }
            self.pendingRedemptions = {
                nodeID: NULL_CLAIM for nodeID in range(MAX_NUM_SENDERS + 1)
            }
            self.numTxsTested = 0

            self.scg_communityGuardDisabled = self.scg.getCommunityGuardDisabled()
            self.scg_suspended = self.scg.getSuspendedState()
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
        st_dstToken = strategy("uint32")
        st_dstAddress = strategy("bytes")
        st_dstChain = strategy("uint32")
        st_message = strategy("bytes")
        st_refundAddress = strategy("bytes")
        st_gasAmount = strategy("uint")

        # KeyManager

        st_sig_key_idx = strategy("uint", max_value=TOTAL_KEYS - 1)
        st_new_key_idx = strategy("uint", max_value=TOTAL_KEYS - 1)
        st_addrs = strategy("address[]", length=MAX_NUM_SENDERS, unique=True)
        st_msg_data = strategy("bytes32")
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)
        st_message_govAction = strategy("bytes32")

        # StateChainGateway

        st_funder = strategy("address", length=MAX_NUM_SENDERS)
        st_nodeID = strategy("uint", max_value=MAX_NUM_SENDERS)
        st_amount = strategy("uint", max_value=MAX_TEST_FUND)
        st_expiry_time_diff = strategy("uint", max_value=REDEMPTION_DELAY * 10)
        # In reality this high amount isn't really realistic, but for the sake of testing
        st_minFunding = strategy("uint", max_value=int(INIT_FUNDING / 2))

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
            st_gasAmount,
            st_refundAddress,
        ):
            args = (
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                st_message,
                st_gasAmount,
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
                            st_gasAmount,
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
            st_gasAmount,
            st_refundAddress,
        ):
            args = (
                st_dstChain,
                st_dstAddress,
                st_dstToken,
                st_message,
                st_gasAmount,
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
                            st_gasAmount,
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
                if (
                    web3.eth.get_balance(str(st_sender)) >= st_native_amount
                    and st_native_amount > 0
                ):
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

        # Get the key that is probably what we want, but also has a low chance of choosing
        # the 'wrong' key which will cause a revert and tests the full range. Maximises useful
        # results whilst still testing the full range.
        def _get_key_prob(self, keyID):
            samples = ([self.keyIDToCurKeys[keyID]] * 100) + self.allKeys
            return choice(samples)

        # Checks if consumeKeyNonce returns the correct value when called with a random sender,
        # signing key, random keyID that the signing key is supposed to be, and random msgData
        def rule_consumeKeyNonce(self, st_sender, st_sig_key_idx, st_msg_data):

            contractMsgHash = Signer.generate_contractMsgHash(
                self.km.consumeKeyNonce, st_msg_data
            )
            sigData = self.allKeys[st_sig_key_idx].generate_sigData(
                Signer.generate_msgHash(
                    contractMsgHash, nonces, self.km.address, st_sender
                ),
                nonces,
            )

            toLog = (st_sender, st_sig_key_idx, st_msg_data)

            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[AGG]:
                print("                    rule_consumeKeyNonce", *toLog)
                tx = self.km.consumeKeyNonce(
                    sigData, contractMsgHash, {"from": st_sender}
                )
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print("        REV_MSG_SIG rule_consumeKeyNonce", *toLog)
                    self.km.consumeKeyNonce(
                        sigData, contractMsgHash, {"from": st_sender}
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
        # in itself, since Hypothesis usually picks.scgall values as part of shrinking
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

        # StateChainGateway

        # Funds a random amount from a random funder to a random nodeID
        def rule_fundStateChainAccount(self, st_funder, st_nodeID, st_amount):
            toLog = (st_nodeID, st_amount)
            if st_nodeID == 0:
                print("        REV_MSG_NZ_BYTES32 rule_fundStateChainAccount", *toLog)
                with reverts(REV_MSG_NZ_BYTES32):
                    self.f.approve(self.scg.address, st_amount, {"from": st_funder})
                    self.scg.fundStateChainAccount(
                        st_nodeID, st_amount, {"from": st_funder}
                    )
            elif st_amount < self.minFunding:
                print("        rule_fundStateChainAccount MIN_FUNDING", *toLog)
                with reverts(REV_MSG_MIN_FUNDING):
                    self.f.approve(self.scg.address, st_amount, {"from": st_funder})
                    self.scg.fundStateChainAccount(
                        st_nodeID, st_amount, {"from": st_funder}
                    )
            elif st_amount > self.flipBals[st_funder]:
                print(
                    "        rule_fundStateChainAccount REV_MSG_ERC20_EXCEED_BAL",
                    *toLog,
                )
                with reverts(REV_MSG_ERC20_EXCEED_BAL):
                    self.f.approve(self.scg.address, st_amount, {"from": st_funder})
                    self.scg.fundStateChainAccount(
                        st_nodeID, st_amount, {"from": st_funder}
                    )
            else:
                print("                    rule_fundStateChainAccount ", *toLog)
                self.f.approve(self.scg.address, st_amount, {"from": st_funder})
                self.scg.fundStateChainAccount(
                    st_nodeID, st_amount, {"from": st_funder}
                )

                self.flipBals[st_funder] -= st_amount
                self.flipBals[self.scg] += st_amount
                self.totalFunding += st_amount

        # Redemptions a random amount from a random nodeID to a random recipient
        def rule_registerRedemption(
            self, st_nodeID, st_funder, st_amount, st_sender, st_expiry_time_diff
        ):
            args = (
                st_nodeID,
                st_amount,
                st_funder,
                getChainTime() + st_expiry_time_diff,
            )
            signer = self._get_key_prob(AGG)
            toLog = (*args, signer, st_sender)

            if self.scg_suspended:
                print("        REV_MSG_GOV_SUSPENDED _registerRedemption")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.scg.registerRedemption,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif st_nodeID == 0:
                print("        NODEID rule_registerRedemption", *toLog)
                with reverts(REV_MSG_NZ_BYTES32):
                    signed_call_km(
                        self.km,
                        self.scg.registerRedemption,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif st_amount == 0:
                print("        AMOUNT rule_registerRedemption", *toLog)
                with reverts(REV_MSG_NZ_UINT):
                    signed_call_km(
                        self.km,
                        self.scg.registerRedemption,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_registerRedemption", signer)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.scg.registerRedemption,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif getChainTime() <= self.pendingRedemptions[st_nodeID][3]:
                print("        REV_MSG_CLAIM_EXISTS rule_registerRedemption", *toLog)
                with reverts(REV_MSG_CLAIM_EXISTS):
                    signed_call_km(
                        self.km,
                        self.scg.registerRedemption,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif st_expiry_time_diff <= REDEMPTION_DELAY:
                print("        REV_MSG_EXPIRY_TOO_SOON rule_registerRedemption", *toLog)
                with reverts(REV_MSG_EXPIRY_TOO_SOON):
                    signed_call_km(
                        self.km,
                        self.scg.registerRedemption,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                print("                    rule_registerRedemption ", *toLog)
                tx = signed_call_km(
                    self.km,
                    self.scg.registerRedemption,
                    *args,
                    signer=signer,
                    sender=st_sender,
                )
                self.pendingRedemptions[st_nodeID] = (
                    st_amount,
                    st_funder,
                    tx.timestamp + REDEMPTION_DELAY,
                    args[3],
                )
                self.lastValidateTime = tx.timestamp

        # Executes a random redemption
        def rule_executeRedemption(self, st_nodeID, st_sender):
            if self.scg_suspended:
                print("        REV_MSG_GOV_SUSPENDED _executeRedemption")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.scg.executeRedemption(st_nodeID, {"from": st_sender})
                return

            redemption = self.pendingRedemptions[st_nodeID]

            # Redemption can be empty
            if not redemption[2] <= getChainTime() or redemption == NULL_CLAIM:
                print("        REV_MSG_NOT_ON_TIME rule_executeRedemption", st_nodeID)
                with reverts(REV_MSG_NOT_ON_TIME):
                    self.scg.executeRedemption(st_nodeID, {"from": st_sender})
            # If it's expired it won't revert regardless of the token balances
            elif (
                self.flipBals[self.scg] < redemption[0]
                and getChainTime() <= redemption[3]
            ):
                print(
                    "        REV_MSG_ERC20_EXCEED_BAL rule_executeRedemption", st_nodeID
                )
                with reverts(REV_MSG_ERC20_EXCEED_BAL):
                    self.scg.executeRedemption(st_nodeID, {"from": st_sender})
            else:
                print("                    rule_executeRedemption", st_nodeID)
                self.scg.executeRedemption(st_nodeID, {"from": st_sender})

                # Redemption not expired
                if getChainTime() <= redemption[3]:
                    self.flipBals[redemption[1]] += redemption[0]
                    self.flipBals[self.scg] -= redemption[0]
                    self.totalFunding -= redemption[0]

                self.pendingRedemptions[st_nodeID] = NULL_CLAIM

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
                    self.scg.setMinFunding(st_minFunding, {"from": st_sender})
            elif st_sender != self.governor:
                print(
                    "        REV_MSG_SIG rule_setMinFunding", st_minFunding, st_sender
                )
                with reverts(REV_MSG_GOV_GOVERNOR):
                    self.scg.setMinFunding(st_minFunding, {"from": st_sender})
            else:
                print(
                    "                    rule_setMinFunding", st_minFunding, st_sender
                )
                self.scg.setMinFunding(st_minFunding, {"from": st_sender})

                self.minFunding = st_minFunding

        # Tries to set the FLIP address. It should have been set right after the deployment.
        def rule_setFlip(self, st_sender, st_funder):
            print("        REV_MSG_NZ_ADDR rule_setFlip", st_sender)
            with reverts(REV_MSG_NZ_ADDR):
                self.scg.setFlip(ZERO_ADDR, {"from": st_sender})

            print("        REV_MSG_FLIP_ADDRESS rule_setFlip", st_sender)
            with reverts(REV_MSG_FLIP_ADDRESS):
                self.scg.setFlip(st_funder, {"from": st_sender})

        # Updates Flip Supply minting/burning stateChainGateway tokens
        def rule_updateFlipSupply(self, st_sender, st_amount_supply, blockNumber_incr):

            scg_inibalance = self.f.balanceOf(self.scg)
            new_total_supply = self.f.totalSupply() + st_amount_supply

            # Avoid newSupplyBlockNumber being a negative number
            newSupplyBlockNumber = max(self.lastSupplyBlockNumber + blockNumber_incr, 0)

            args = (
                new_total_supply,
                newSupplyBlockNumber,
            )
            signer = self._get_key_prob(AGG)
            toLog = (*args, signer, st_sender, st_amount_supply)

            if self.scg_suspended:
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.scg.updateFlipSupply,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_updateFlipSupply", *toLog)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.scg.updateFlipSupply,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

            elif newSupplyBlockNumber <= self.lastSupplyBlockNumber:
                print("        REV_MSG_BLOCK rule_updateFlipSupply", *toLog)
                with reverts(REV_MSG_OLD_FLIP_SUPPLY_UPDATE):
                    signed_call_km(
                        self.km,
                        self.scg.updateFlipSupply,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                if scg_inibalance + st_amount_supply < 0:
                    with reverts(REV_MSG_BURN_BALANCE):
                        print(
                            "        REV_MSG_BURN_BALANCE rule_updateFlipSupply", *toLog
                        )
                        signed_call_km(
                            self.km,
                            self.scg.updateFlipSupply,
                            *args,
                            signer=signer,
                            sender=st_sender,
                        )
                else:
                    print("                    rule_updateFlipSupply", *toLog)
                    tx = signed_call_km(
                        self.km,
                        self.scg.updateFlipSupply,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )

                    assert self.f.totalSupply() == new_total_supply
                    assert (
                        self.f.balanceOf(self.scg) == scg_inibalance + st_amount_supply
                    )

                    self.flipBals[self.scg] += st_amount_supply
                    self.lastSupplyBlockNumber = newSupplyBlockNumber
                    self.lastValidateTime = tx.timestamp

        # FLIP

        def rule_issue_rev_issuer(self, st_sender, st_amount):
            # st_sender should never match the stateChainGateway issuer
            print("        REV_MSG_FLIP rule_issue_rev_iisuer", st_sender)
            with reverts(REV_MSG_FLIP_ISSUER):
                self.f.mint(st_sender, st_amount, {"from": st_sender})
            with reverts(REV_MSG_FLIP_ISSUER):
                self.f.burn(st_sender, st_amount, {"from": st_sender})
            with reverts(REV_MSG_FLIP_ISSUER):
                self.f.updateIssuer(st_sender, {"from": st_sender})

        # AggKeyNonceConsumer - upgradability

        # Deploys a new keyManager and updates all the references to it
        def rule_upgrade_keyManager(self, st_sender):
            aggKeyNonceConsumers = [self.scg, self.v]

            # Reusing current keyManager aggregateKey for simplicity.
            newKeyManager = deploy_new_keyManager(
                st_sender,
                KeyManager,
                self.km.getAggregateKey(),
                self.governor,
                self.communityKey,
            )

            signer = self._get_key_prob(AGG)

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

        # Deploys a new Vault and transfers the funds from the old Vault to the new one
        def rule_upgrade_Vault(self, st_sender, st_sleep_time):
            newVault = deploy_new_vault(st_sender, Vault, KeyManager, self.km)

            # Transfer all the remaining native and other funds (TokenA & TokenB) to new Vault
            iniNativeBalance = self.v.balance()
            initTokenABalance = self.tokenA.balanceOf(self.v)
            iniTokenBBalance = self.tokenB.balanceOf(self.v)

            amountsToTransfer = [
                iniNativeBalance,
                initTokenABalance,
                iniTokenBBalance,
            ]

            tokens = [NATIVE_ADDR, self.tokenA, self.tokenB]
            recipients = [newVault, newVault, newVault]
            args = [craftTransferParamsArray(tokens, recipients, amountsToTransfer)]

            signer = self._get_key_prob(AGG)
            if self.v_suspended:
                print(
                    "        REV_MSG_GOV_SUSPENDED rule_upgrade_Vault",
                    *amountsToTransfer,
                )
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.v.transferBatch,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print("        REV_MSG_SIG rule_upgrade_Vault", *amountsToTransfer)
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.v.transferBatch,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:

                chain.sleep(st_sleep_time)

                print("                    rule_upgrade_vault", *amountsToTransfer)

                tx = signed_call_km(
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

                # Update state variables
                self.v = newVault
                self.lastValidateTime = tx.timestamp
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

        # Deploys a new State Chain Gateway and transfers the FLIP tokens from the old SM to the new one
        def rule_upgrade_stateChainGateway(self, st_sender, st_sleep_time):
            (_, newStateChainGateway) = deploy_new_stateChainGateway(
                st_sender,
                KeyManager,
                StateChainGateway,
                FLIP,
                DeployerStateChainGateway,
                self.km.address,
                self.f.address,
                INIT_MIN_FUNDING,
            )

            args = (JUNK_HEX, 1, newStateChainGateway, 1)
            signer = self._get_key_prob(AGG)

            if self.scg_suspended:
                print("        REV_MSG_GOV_SUSPENDED rule_upgrade_stateChainGateway")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(
                        self.km,
                        self.scg.registerRedemption,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            elif signer != self.keyIDToCurKeys[AGG]:
                print(
                    "        REV_MSG_SIG rule_upgrade_stateChainGateway",
                )
                with reverts(REV_MSG_SIG):
                    signed_call_km(
                        self.km,
                        self.scg.registerRedemption,
                        *args,
                        signer=signer,
                        sender=st_sender,
                    )
            else:
                chain.sleep(st_sleep_time)

                # Generate redemption to move all FLIP to new stateChainGateway
                expiryTime = getChainTime() + (REDEMPTION_DELAY * 10)
                redemptionAmount = self.flipBals[self.scg]
                # Register Redemption to transfer all flip
                args = (
                    JUNK_HEX,
                    redemptionAmount,
                    newStateChainGateway,
                    expiryTime,
                )
                signed_call_km(
                    self.km,
                    self.scg.registerRedemption,
                    *args,
                    signer=signer,
                    sender=st_sender,
                )

                chain.sleep(st_sleep_time)
                if st_sleep_time < REDEMPTION_DELAY:
                    with reverts(REV_MSG_NOT_ON_TIME):
                        print(
                            "        REV_MSG_SIG rule_upgrade_stateChainGateway",
                            st_sleep_time,
                        )
                        self.scg.executeRedemption(JUNK_HEX, {"from": st_sender})

                chain.sleep(REDEMPTION_DELAY * 2)

                print(
                    "                   rule_executeRedemption",
                    newStateChainGateway.address,
                )
                assert self.f.balanceOf(newStateChainGateway) == 0
                assert self.f.balanceOf(self.scg) == self.flipBals[self.scg]

                self.scg.executeRedemption(JUNK_HEX, {"from": st_sender})

                assert self.f.balanceOf(newStateChainGateway) == self.flipBals[self.scg]
                assert self.f.balanceOf(self.scg) == 0

                self._updateBalancesOnUpgrade(self.scg, newStateChainGateway)

                tx = signed_call_km(
                    self.km,
                    self.scg.updateFlipIssuer,
                    newStateChainGateway.address,
                    signer=signer,
                    sender=st_sender,
                )

                self.scg = newStateChainGateway
                self.minFunding = INIT_MIN_FUNDING
                self.lastValidateTime = tx.timestamp
                self.scg_communityGuardDisabled = False
                self.communityKey = self.communityKey
                self.scg_suspended = False
                self.lastSupplyBlockNumber = 0

                # Reset all pending redemptions
                self.pendingRedemptions = {
                    nodeID: NULL_CLAIM for nodeID in range(MAX_NUM_SENDERS + 1)
                }

        # Governance Community Guarded

        # Suspends the State Chain Gateway if st_sender matches the governor address.
        def rule_suspend_stateChainGateway(self, st_sender, st_addr):
            if st_sender == self.governor:
                # To avoid suspending it very often
                if st_addr != st_sender:
                    return
                if self.scg_suspended:
                    print("        REV_MSG_GOV_SUSPENDED _suspend")
                    with reverts(REV_MSG_GOV_SUSPENDED):
                        self.scg.suspend({"from": st_sender})
                else:
                    print("                    rule_suspend", st_sender)
                    self.scg.suspend({"from": st_sender})
                    self.scg_suspended = True
            else:
                print("        REV_MSG_GOV_GOVERNOR _suspend")
                with reverts(REV_MSG_GOV_GOVERNOR):
                    self.scg.suspend({"from": st_sender})

        # Resumes the State Chain Gateway if it is suspended. We always resume it to avoid
        # having the stateChainGateway suspended too often
        def rule_resume_stateChainGateway(self, st_sender):
            if self.scg_suspended:
                if st_sender != self.governor:
                    with reverts(REV_MSG_GOV_GOVERNOR):
                        self.scg.resume({"from": st_sender})
                # Always resume
                print("                    rule_resume", st_sender)
                self.scg.resume({"from": self.governor})
                self.scg_suspended = False
            else:
                print("        REV_MSG_GOV_NOT_SUSPENDED _resume", st_sender)
                with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                    self.scg.resume({"from": self.governor})

        # Suspends the State Chain Gateway if st_sender matches the governor address.
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

        # Resumes the State Chain Gateway if it is suspended. We always resume it to avoid
        # having the stateChainGateway suspended too often
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

        # Enable State Chain Gateway's community Guard
        def rule_scg_enableCommunityGuard(self, st_sender):
            if self.scg_communityGuardDisabled:
                if st_sender != self.communityKey:
                    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                        self.scg.enableCommunityGuard({"from": st_sender})
                # Always enable
                print("                    rule.scg_enableCommunityGuard", st_sender)
                self.scg.enableCommunityGuard({"from": self.communityKey})
                self.scg_communityGuardDisabled = False
            else:
                print(
                    "        REV_MSG_GOV_ENABLED_GUARD .scg_enableCommunityGuard",
                    st_sender,
                )
                with reverts(REV_MSG_GOV_ENABLED_GUARD):
                    self.scg.enableCommunityGuard({"from": self.communityKey})

        # Disable State Chain Gateway's community Guard
        def rule_scg_disableCommunityGuard(self, st_sender):
            if not self.scg_communityGuardDisabled:
                if st_sender != self.communityKey:
                    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                        self.scg.disableCommunityGuard({"from": st_sender})
                # Always disable
                print("                    rule.scg_disableCommunityGuard", st_sender)
                self.scg.disableCommunityGuard({"from": self.communityKey})
                self.scg_communityGuardDisabled = True
            else:
                print(
                    "        REV_MSG_GOV_DISABLED_GUARD .scg_disableCommunityGuard",
                    st_sender,
                )
                with reverts(REV_MSG_GOV_DISABLED_GUARD):
                    self.scg.disableCommunityGuard({"from": self.communityKey})

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

        # Governance attemps to withdraw FLIP from the State Chain Gateway in case of emergency
        def rule_scg_govWithdrawal(self, st_sender):
            if self.scg_communityGuardDisabled:
                if st_sender != self.governor:
                    with reverts(REV_MSG_GOV_GOVERNOR):
                        self.scg.govWithdraw({"from": st_sender})

                if self.scg_suspended:
                    print("                    rule_govWithdrawal", st_sender)
                    self.scg.govWithdraw({"from": self.governor})
                    # Governor has all the FLIP - do the checking and return the tokens for the invariant check
                    assert (
                        self.f.balanceOf(self.governor)
                        == self.flipBals[self.governor] + self.flipBals[self.scg]
                    )
                    assert self.f.balanceOf(self.scg) == 0
                    self.f.transfer(
                        self.scg, self.flipBals[self.scg], {"from": self.governor}
                    )
                else:
                    print("        REV_MSG_GOV_NOT_SUSPENDED _govWithdrawal")
                    with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                        self.scg.govWithdraw({"from": self.governor})
            else:
                print("        REV_MSG_GOV_ENABLED_GUARD _govWithdrawal")
                with reverts(REV_MSG_GOV_ENABLED_GUARD):
                    self.scg.govWithdraw({"from": self.governor})

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

        # Transfer native to the stateChainGateway to check govWithdrawalNative. Using st_funder to make sure it is a key in the nativeBals dict
        def _transfer_native_scg(self, st_funder, st_native_amount):
            self._transfer_native(st_funder, self.scg, st_native_amount)

        # Transfer native to the stateChainGateway to check govWithdrawalNative. Using st_funder to make sure it is a key in the nativeBals dict
        def _transfer_native_km(self, st_funder, st_native_amount):
            self._transfer_native(st_funder, self.km, st_native_amount)

        # Transfer native from sender to receiver. Both need be keys in the nativeBals dict
        def _transfer_native(self, sender, receiver, amount):
            if self.nativeBals[sender] >= amount:
                print(
                    "                    rule_transfer_native", sender, receiver, amount
                )
                sender.transfer(receiver, amount)
                self.nativeBals[sender] -= amount
                self.nativeBals[receiver] += amount

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
        # NOTE: Error in self.nativeBals assertion - calculateGasSpentByAddress seems to be.scgaller than expected and intermittently the native balance
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
            assert self.km.address == self.v.getKeyManager() == self.scg.getKeyManager()

            assert self.scg.getFLIP() == self.f.address

        # Check the keys are correct after every tx
        def invariant_keys(self):
            assert (
                self.km.getAggregateKey() == self.keyIDToCurKeys[AGG].getPubDataWith0x()
            )
            assert (
                self.governor
                == self.km.getGovernanceKey()
                == self.scg.getGovernor()
                == self.v.getGovernor()
            )
            assert (
                self.communityKey
                == self.km.getCommunityKey()
                == self.scg.getCommunityKey()
                == self.v.getCommunityKey()
            )

        # Check the state variables after every tx
        def invariant_state_vars(self):
            assert (
                self.scg.getLastSupplyUpdateBlockNumber() == self.lastSupplyBlockNumber
            )
            assert self.scg.getMinimumFunding() == self.minFunding
            assert (
                self.scg_communityGuardDisabled == self.scg.getCommunityGuardDisabled()
            )
            assert self.scg_suspended == self.scg.getSuspendedState()
            assert self.v_communityGuardDisabled == self.v.getCommunityGuardDisabled()
            assert self.v_suspended == self.v.getSuspendedState()
            assert self.km.getLastValidateTime() == self.lastValidateTime
            for nodeID, redemption in self.pendingRedemptions.items():
                assert self.scg.getPendingRedemption(nodeID) == redemption
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
        cfDeploy,
        Deposit,
        Token,
        CFReceiverMock,
        MockUSDT,
        settings=settings,
    )
