from ctypes import addressof
from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy, contract_strategy
from hypothesis import strategies as hypStrat
from random import choice, choices
from shared_tests import *

settings = {"stateful_step_count": 100, "max_examples": 50}


# Stateful test for all functions in the Vault
def test_vault(BaseStateMachine, state_machine, a, cfDeploy, Deposit, Token):

    # The max swapID to use. SwapID is needed as a salt to create a unique create2
    # address, and for ease they're used between 1 and MAX_SWAPID inclusive in this test
    # (since 0 will cause a revert when fetching).
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

    class StateMachine(BaseStateMachine):

        """
        This test calls functions from Vault in random orders. It uses a set number of Deposit
        contracts/create2 addresses for native & each token (MAX_SWAPID amount of each,
        3 * MAX_SWAPID total) and also randomly sends native and the 2 ERC20 tokens to the create2
        addresses that correspond to the create2 addresses so that something can actually be fetched
        and transferred.
        The parameters used are so that they're small enough to increase the likelihood of the same
        address being used in multiple interactions (e.g. 2  x transfers then a fetch etc) and large
        enough to ensure there's variety in them
        """

        # Set up the initial test conditions once
        def __init__(cls, a, cfDeploy, Deposit, Token):
            # cls.aaa = {addr: addr for addr, addr in enumerate(a)}
            super().__init__(cls, a, cfDeploy)

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
            cls.allAddrs = [
                *[addr.address for addr in a[:MAX_NUM_SENDERS]],
                *cls.create2EthAddrs,
                *cls.create2TokenAAddrs,
                *cls.create2TokenBAddrs,
                cls.v.address,
            ]

            # Workaround for initial Vault Balance
            cls.initialVaultBalance = web3.eth.get_balance(cls.v.address)

        # Reset the local versions of state to compare the contract to after every run
        def setup(self):
            self.nativeBals = {
                # Accounts within "a" will have INIT_NATIVE_BAL - gas spent in setup/deployment
                addr: web3.eth.get_balance(addr)
                if addr in a
                else (self.initialVaultBalance if addr == self.v.address else 0)
                for addr in self.allAddrs
            }
            self.tokenABals = {
                addr: INIT_TOKEN_AMNT if addr in a else 0 for addr in self.allAddrs
            }
            self.tokenBBals = {
                addr: INIT_TOKEN_AMNT if addr in a else 0 for addr in self.allAddrs
            }
            # Store initial transaction number for each of the accounts to later calculate gas spendings
            self.iniTransactionNumber = {}
            for addr in self.allAddrs:
                self.iniTransactionNumber[addr] = len(history.filter(sender=addr))

            self.numTxsTested = 0
            self.governor = cfDeploy.gov
            self.communityKey = cfDeploy.communityKey

            self.communityGuardDisabled = self.v.getCommunityGuardDisabled()
            self.suspended = self.v.getSuspendedState()
            self.swapsEnabled = False

            # Dictionary swapID:deployedAddress
            self.deployedDeposits = dict()

        # Variables that will be a random value with each fcn/rule called

        st_native_amount = strategy("uint", max_value=MAX_NATIVE_SEND)
        st_native_amounts = strategy("uint[]", max_value=MAX_NATIVE_SEND)
        st_token = contract_strategy("Token")
        st_tokens = hypStrat.lists(st_token)
        st_token_amount = strategy("uint", max_value=MAX_TOKEN_SEND)
        st_swapID = strategy("uint", max_value=MAX_SWAPID)
        st_swapIDs = strategy("uint[]", min_value=0, max_value=MAX_SWAPID, unique=True)
        # Only want the 1st 5 addresses so that the chances of multiple
        # txs occurring from the same address is greatly increased while still
        # ensuring diversity in senders
        st_sender = strategy("address", length=MAX_NUM_SENDERS)
        st_sender_any = strategy("address")
        st_recip = strategy("address", length=MAX_NUM_SENDERS)
        st_recips = strategy("address[]", length=MAX_NUM_SENDERS, unique=True)
        st_egressParams = strategy("string")
        st_egressReceiver = strategy("bytes32", exclude=(0).to_bytes(32, "big"))

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
            tranTotals = {
                tok: sum(
                    [st_native_amounts[i] for i, x in enumerate(tranTokens) if x == tok]
                )
                for tok in self.tokensList
            }
            validEthIdxs = getValidTranIdxs(
                tranTokens,
                st_native_amounts,
                self.nativeBals[self.v.address] + fetchEthTotal,
                NATIVE_ADDR,
            )
            tranTotals[NATIVE_ADDR] = sum(
                [
                    st_native_amounts[i]
                    for i, x in enumerate(tranTokens)
                    if x == NATIVE_ADDR and i in validEthIdxs
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

            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _allBatch")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    signed_call_km(self.km, self.v.allBatch, *args, sender=st_sender)
            elif (
                tranTotals[self.tokenA] - fetchTokenATotal
                > self.tokenABals[self.v.address]
                or tranTotals[self.tokenB] - fetchTokenBTotal
                > self.tokenBBals[self.v.address]
            ):
                print("        NOT ENOUGH TOKENS IN VAULT rule_allBatch", *toLog)
                with reverts(REV_MSG_ERC20_EXCEED_BAL):
                    signed_call_km(self.km, self.v.allBatch, *args, sender=st_sender)
            else:
                print("                    rule_allBatch", *toLog)
                signed_call_km(self.km, self.v.allBatch, *args, sender=st_sender)

                # Alter bals from the fetches
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
                        self.nativeBals[self.v.address] += self.nativeBals[addr]
                        self.nativeBals[addr] = 0
                    else:
                        if tok == self.tokenA:
                            self.tokenABals[self.v.address] += self.tokenABals[addr]
                            self.tokenABals[addr] = 0
                        elif tok == self.tokenB:
                            self.tokenBBals[self.v.address] += self.tokenBBals[addr]
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
                            self.nativeBals[self.v.address] -= am
                    elif tok == self.tokenA:
                        self.tokenABals[rec] += am
                        self.tokenABals[self.v.address] -= am
                    elif tok == self.tokenB:
                        self.tokenBBals[rec] += am
                        self.tokenBBals[self.v.address] -= am
                    else:
                        assert False, "Panic"

        # # Transfers native or tokens out the vault. Want this to be called by rule_vault_transfer_native
        # # etc individually and not directly since they're all the same just with a different tokenAddr
        # # input
        # def _vault_transfer(
        #     self, bals, tokenAddr, st_sender, st_recip, st_native_amount
        # ):
        #     args = [[tokenAddr, st_recip, st_native_amount]]
        #     toLog = (*args, st_sender)

        #     if self.suspended:
        #         print("        REV_MSG_GOV_SUSPENDED _vault_transfer")
        #         with reverts(REV_MSG_GOV_SUSPENDED):
        #             signed_call_km(self.km, self.v.transfer, *args, sender=st_sender)

        #     elif st_native_amount == 0:
        #         print("        REV_MSG_NZ_UINT _vault_transfer", *toLog)
        #         with reverts(REV_MSG_NZ_UINT):
        #             signed_call_km(self.km, self.v.transfer, *args, sender=st_sender)

        #     elif bals[self.v.address] < st_native_amount and tokenAddr != NATIVE_ADDR:
        #         print("        NOT ENOUGH TOKENS IN VAULT _vault_transfer", *toLog)
        #         with reverts(REV_MSG_ERC20_EXCEED_BAL):
        #             signed_call_km(self.km, self.v.transfer, *args, sender=st_sender)

        #     else:
        #         print("                    _vault_transfer", *toLog)
        #         signed_call_km(self.km, self.v.transfer, *args, sender=st_sender)

        #         if bals[self.v.address] >= st_native_amount or tokenAddr != NATIVE_ADDR:
        #             bals[self.v.address] -= st_native_amount
        #             bals[st_recip] += st_native_amount

        # def rule_vault_transfer_native(self, st_sender, st_recip, st_native_amount):
        #     self._vault_transfer(
        #         self.nativeBals, NATIVE_ADDR, st_sender, st_recip, st_native_amount
        #     )

        # def rule_vault_transfer_tokenA(self, st_sender, st_recip, st_token_amount):
        #     self._vault_transfer(
        #         self.tokenABals, self.tokenA, st_sender, st_recip, st_token_amount
        #     )

        # def rule_vault_transfer_tokenB(self, st_sender, st_recip, st_token_amount):
        #     self._vault_transfer(
        #         self.tokenBBals, self.tokenB, st_sender, st_recip, st_token_amount
        #     )

        # # Send any combination of native/tokenA/tokenB out of the vault. Using st_native_amounts
        # # for both native amounts and token amounts here because its max is within the bounds of
        # # both native and tokens.
        # def rule_vault_transferBatch(self, st_sender, st_recips, st_native_amounts):
        #     minLen = trimToShortest([st_recips, st_native_amounts])
        #     tokens = choices(self.tokensList, k=minLen)
        #     tranTotals = {
        #         tok: sum(
        #             [st_native_amounts[i] for i, x in enumerate(tokens) if x == tok]
        #         )
        #         for tok in self.tokensList
        #     }
        #     validEthIdxs = getValidTranIdxs(
        #         tokens, st_native_amounts, self.nativeBals[self.v.address], NATIVE_ADDR
        #     )
        #     tranTotals[NATIVE_ADDR] = sum(
        #         [
        #             st_native_amounts[i]
        #             for i, x in enumerate(tokens)
        #             if x == NATIVE_ADDR and i in validEthIdxs
        #         ]
        #     )

        #     args = [craftTransferParamsArray(tokens, st_recips, st_native_amounts)]

        #     toLog = (*args, st_sender)

        #     if self.suspended:
        #         print("        REV_MSG_GOV_SUSPENDED _vault_transferBatch")
        #         with reverts(REV_MSG_GOV_SUSPENDED):
        #             signed_call_km(
        #                 self.km, self.v.transferBatch, *args, sender=st_sender
        #             )
        #     elif (
        #         tranTotals[self.tokenA] > self.tokenABals[self.v.address]
        #         or tranTotals[self.tokenB] > self.tokenBBals[self.v.address]
        #     ):
        #         print(
        #             "        NOT ENOUGH TOKENS IN VAULT rule_vault_transferBatch",
        #             *toLog,
        #         )
        #         with reverts():
        #             signed_call_km(
        #                 self.km, self.v.transferBatch, *args, sender=st_sender
        #             )
        #     else:
        #         print("                    rule_vault_transferBatch", *toLog)
        #         signed_call_km(self.km, self.v.transferBatch, *args, sender=st_sender)

        #         for i in range(len(st_recips)):
        #             if tokens[i] == NATIVE_ADDR:
        #                 if i in validEthIdxs:
        #                     self.nativeBals[st_recips[i]] += st_native_amounts[i]
        #                     self.nativeBals[self.v.address] -= st_native_amounts[i]
        #             elif tokens[i] == self.tokenA:
        #                 self.tokenABals[st_recips[i]] += st_native_amounts[i]
        #                 self.tokenABals[self.v.address] -= st_native_amounts[i]
        #             elif tokens[i] == self.tokenB:
        #                 self.tokenBBals[st_recips[i]] += st_native_amounts[i]
        #                 self.tokenBBals[self.v.address] -= st_native_amounts[i]
        #             else:
        #                 assert False, "Panic"

        # # Transfers native from a user/sender to one of the depositEth create2 addresses
        # def rule_transfer_native_to_depositEth(
        #     self, st_sender, st_swapID, st_native_amount
        # ):
        #     # Since st_swapID = 0 won't be able to be fetched (reverts on empty input),
        #     # no point sending native to that corresponding addr
        #     if st_swapID != 0 and self.nativeBals[st_sender] >= st_native_amount:
        #         print(
        #             "                    rule_transfer_native_to_depositEth",
        #             st_sender,
        #             st_swapID,
        #             st_native_amount,
        #         )
        #         depositAddr = getCreate2Addr(
        #             self.v.address,
        #             cleanHexStrPad(st_swapID),
        #             Deposit,
        #             cleanHexStrPad(NATIVE_ADDR),
        #         )
        #         st_sender.transfer(depositAddr, st_native_amount)

        #         self.nativeBals[st_sender] -= st_native_amount
        #         self.nativeBals[depositAddr] += st_native_amount

        # # Transfers a token from a user/sender to one of the depositEth create2 addresses.
        # # This isn't called directly since rule_transfer_tokens_to_depositTokenA etc use it
        # # in the same way but with a different tokenAddr
        # def _transfer_tokens_to_depositToken(
        #     self, bals, token, st_sender, st_swapID, st_token_amount
        # ):
        #     # Since st_swapID = 0 won't be able to be fetched (reverts on empty input),
        #     # no point sending native to that corresponding addr
        #     if st_swapID != 0 and bals[st_sender] >= st_token_amount:
        #         print(
        #             "                    _transfer_tokens_to_depositToken",
        #             token,
        #             st_sender,
        #             st_swapID,
        #             st_token_amount,
        #         )
        #         depositAddr = getCreate2Addr(
        #             self.v.address,
        #             cleanHexStrPad(st_swapID),
        #             Deposit,
        #             cleanHexStrPad(token.address),
        #         )
        #         token.transfer(depositAddr, st_token_amount, {"from": st_sender})

        #         bals[st_sender] -= st_token_amount
        #         bals[depositAddr] += st_token_amount

        # # Deposits tokenA from a user to a tokenA create2
        # def rule_transfer_tokens_to_depositTokenA(
        #     self, st_sender, st_swapID, st_token_amount
        # ):
        #     self._transfer_tokens_to_depositToken(
        #         self.tokenABals, self.tokenA, st_sender, st_swapID, st_token_amount
        #     )

        # # Deposits tokenB from a user to a tokenB create2
        # def rule_transfer_tokens_to_depositTokenB(
        #     self, st_sender, st_swapID, st_token_amount
        # ):
        #     self._transfer_tokens_to_depositToken(
        #         self.tokenBBals, self.tokenB, st_sender, st_swapID, st_token_amount
        #     )

        # # Fetch the native deposit of a random create2
        # def rule_fetchNative(self, st_sender, st_swapID):
        #     if self.suspended:
        #         print("        REV_MSG_GOV_SUSPENDED _fetchDepositNative")
        #         with reverts(REV_MSG_GOV_SUSPENDED):
        #             signed_call_km(
        #                 self.km,
        #                 self.v.deployAndFetchBatch,
        #                 [[st_swapID, NATIVE_ADDR]],
        #                 sender=st_sender,
        #             )
        #     else:
        #         print(
        #             "                    rule_fetchDepositNative", st_sender, st_swapID
        #         )
        #         if st_swapID not in self.deployedDeposits:
        #             signed_call_km(
        #                 self.km,
        #                 self.v.deployAndFetchBatch,
        #                 [[st_swapID, NATIVE_ADDR]],
        #                 sender=st_sender,
        #             )

        #             depositAddr = getCreate2Addr(
        #                 self.v.address,
        #                 cleanHexStrPad(st_swapID),
        #                 Deposit,
        #                 cleanHexStrPad(NATIVE_ADDR),
        #             )
        #             self.deployedDeposits[st_swapID] = depositAddr
        #         else:
        #             depositAddr = self.deployedDeposits[st_swapID]
        #             signed_call_km(
        #                 self.km,
        #                 self.v.fetchBatch,
        #                 [[depositAddr, NATIVE_ADDR]],
        #                 sender=st_sender,
        #             )

        #         depositBal = self.nativeBals[depositAddr]
        #         self.nativeBals[depositAddr] -= depositBal
        #         self.nativeBals[self.v.address] += depositBal

        # def rule_fetchDepositNativeBatch(self, st_sender, st_swapIDs):
        #     if self.suspended:
        #         print("        REV_MSG_GOV_SUSPENDED _fetchDepositNativeBatch")
        #         with reverts(REV_MSG_GOV_SUSPENDED):
        #             signed_call_km(
        #                 self.km,
        #                 self.v.deployAndFetchBatch,
        #                 craftDeployFetchParamsArray(
        #                     st_swapIDs, [NATIVE_ADDR] * len(st_swapIDs)
        #                 ),
        #                 sender=st_sender,
        #             )
        #         return
        #     print(
        #         "                    rule_fetchDepositNativeBatch",
        #         st_sender,
        #         st_swapIDs,
        #     )
        #     used_addresses = []
        #     non_used_swapIDs = []
        #     for st_swapID in st_swapIDs:
        #         if st_swapID in self.deployedDeposits:
        #             depositAddr = self.deployedDeposits[st_swapID]
        #             used_addresses.append(depositAddr)

        #         else:
        #             non_used_swapIDs.append(st_swapID)
        #             depositAddr = getCreate2Addr(
        #                 self.v.address,
        #                 cleanHexStrPad(st_swapID),
        #                 Deposit,
        #                 cleanHexStrPad(NATIVE_ADDR),
        #             )
        #             self.deployedDeposits[st_swapID] = depositAddr

        #         # Accounting here to reuse the loop logic
        #         self.nativeBals[self.v.address] += self.nativeBals[depositAddr]
        #         self.nativeBals[depositAddr] = 0

        #     deployFetchParamsArray = craftDeployFetchParamsArray(
        #         non_used_swapIDs, [NATIVE_ADDR] * len(non_used_swapIDs)
        #     )

        #     signed_call_km(
        #         self.km,
        #         self.v.deployAndFetchBatch,
        #         deployFetchParamsArray,
        #         sender=st_sender,
        #     )

        #     fetchParamsArray = craftFetchParamsArray(
        #         used_addresses, [NATIVE_ADDR] * len(used_addresses)
        #     )
        #     signed_call_km(
        #         self.km, self.v.fetchBatch, fetchParamsArray, sender=st_sender
        #     )

        # # Fetch the token deposit of a random create2
        # def _fetchDepositToken(self, bals, token, st_sender, st_swapID):
        #     args = [[st_swapID, token.address]]
        #     toLog = (*args, st_sender)

        #     if self.suspended:
        #         print("        REV_MSG_GOV_SUSPENDED _fetchDepositToken")
        #         with reverts(REV_MSG_GOV_SUSPENDED):
        #             signed_call_km(
        #                 self.km, self.v.deployAndFetchBatch, args, sender=st_sender
        #             )
        #     else:
        #         print("                    _fetchDepositToken", *toLog)

        #         if st_swapID not in self.deployedDeposits:
        #             signed_call_km(
        #                 self.km, self.v.deployAndFetchBatch, args, sender=st_sender
        #             )
        #             depositAddr = getCreate2Addr(
        #                 self.v.address,
        #                 cleanHexStrPad(st_swapID),
        #                 Deposit,
        #                 cleanHexStrPad(token.address),
        #             )
        #             self.deployedDeposits[st_swapID] = depositAddr
        #         else:
        #             depositAddr = self.deployedDeposits[st_swapID]
        #             signed_call_km(
        #                 self.km,
        #                 self.v.fetchBatch,
        #                 [[depositAddr, token.address]],
        #                 sender=st_sender,
        #             )

        #         depositBal = bals[depositAddr]
        #         bals[depositAddr] -= depositBal
        #         bals[self.v.address] += depositBal

        # # Fetch the tokenA deposit of a random create2
        # def rule_fetchDepositToken_tokenA(self, st_sender, st_swapID):
        #     self._fetchDepositToken(self.tokenABals, self.tokenA, st_sender, st_swapID)

        # # Fetch the tokenB deposit of a random create2
        # def rule_fetchDepositToken_tokenB(self, st_sender, st_swapID):
        #     self._fetchDepositToken(self.tokenBBals, self.tokenB, st_sender, st_swapID)

        # # Fetches random tokens from random swapID. Since there's no real way
        # # to get the lengths of the input arrays to be the same most of the time, I'm going to have to
        # # use a random number to determine whether or not to concat all arrays to the
        # # length of the shortest so that we'll get mostly valid txs and maximise usefulness. The
        # # easiest random num to use is the length of the arrays themselves - I'm gonna use '3' as the
        # # magic shortest length that should trigger not concating for no particular reason
        # def rule_fetchDepositTokenBatch(self, st_sender, st_swapIDs, st_tokens):

        #     trimToShortest([st_swapIDs, st_tokens])

        #     args = [craftDeployFetchParamsArray(st_swapIDs, st_tokens)]
        #     toLog = (*args, st_sender)
        #     if self.suspended:
        #         print("        REV_MSG_GOV_SUSPENDED _fetchDepositTokenBatch")
        #         with reverts(REV_MSG_GOV_SUSPENDED):
        #             signed_call_km(
        #                 self.km, self.v.deployAndFetchBatch, *args, sender=st_sender
        #             )
        #     else:
        #         print("                    rule_fetchDepositTokenBatch", *toLog)

        #         fetchParamsArray = []
        #         deployFetchParamsArray = []

        #         for st_swapID, token in zip(st_swapIDs, st_tokens):
        #             if st_swapID in self.deployedDeposits:
        #                 fetchParamsArray.append(
        #                     [self.deployedDeposits[st_swapID], token.address]
        #                 )
        #                 depositAddr = self.deployedDeposits[st_swapID]

        #             else:
        #                 deployFetchParamsArray.append([st_swapID, token.address])
        #                 depositAddr = getCreate2Addr(
        #                     self.v.address,
        #                     cleanHexStrPad(st_swapID),
        #                     Deposit,
        #                     cleanHexStrPad(token.address),
        #                 )
        #                 self.deployedDeposits[st_swapID] = depositAddr

        #             # Accounting here to reuse the loop logic
        #             if token == self.tokenA:
        #                 self.tokenABals[self.v.address] += self.tokenABals[depositAddr]
        #                 self.tokenABals[depositAddr] = 0
        #             elif token == self.tokenB:
        #                 self.tokenBBals[self.v.address] += self.tokenBBals[depositAddr]
        #                 self.tokenBBals[depositAddr] = 0
        #             else:
        #                 assert False, "Panicc"

        #         signed_call_km(
        #             self.km,
        #             self.v.deployAndFetchBatch,
        #             deployFetchParamsArray,
        #             sender=st_sender,
        #         )

        #         signed_call_km(
        #             self.km, self.v.fetchBatch, fetchParamsArray, sender=st_sender
        #         )

        # # Sleep AGG_KEY_EMERGENCY_TIMEOUT
        # def rule_sleep_14_days(self):
        #     print("                    rule_sleep_14_days")
        #     chain.sleep(AGG_KEY_EMERGENCY_TIMEOUT)

        # # Suspends the stake Manager if st_sender matches the governor address. It has
        # # has a 1/20 chance of being the governor - don't want to suspend it too often.
        # def rule_suspend(self, st_sender_any):
        #     if st_sender_any == self.governor:
        #         if self.suspended:
        #             print("        REV_MSG_GOV_SUSPENDED _suspend")
        #             with reverts(REV_MSG_GOV_SUSPENDED):
        #                 self.v.suspend({"from": st_sender_any})
        #         else:
        #             print("                    rule_suspend", st_sender_any)
        #             self.v.suspend({"from": st_sender_any})
        #             self.suspended = True
        #     else:
        #         print("        REV_MSG_GOV_GOVERNOR _suspend")
        #         with reverts(REV_MSG_GOV_GOVERNOR):
        #             self.v.suspend({"from": st_sender_any})

        # # Resumes the stake Manager if it is suspended. We always resume it to avoid
        # # having the stakeManager suspended too often
        # def rule_resume(self, st_sender):
        #     if self.suspended:
        #         if st_sender != self.governor:
        #             with reverts(REV_MSG_GOV_GOVERNOR):
        #                 self.v.resume({"from": st_sender})
        #         # Always resume
        #         print("                    rule_resume", st_sender)
        #         self.v.resume({"from": self.governor})
        #         self.suspended = False
        #     else:
        #         print("        REV_MSG_GOV_NOT_SUSPENDED _resume", st_sender)
        #         with reverts(REV_MSG_GOV_NOT_SUSPENDED):
        #             self.v.resume({"from": self.governor})

        # # Enable community Guard
        # def rule_enableCommunityGuard(self, st_sender):
        #     if self.communityGuardDisabled:
        #         if st_sender != self.communityKey:
        #             with reverts(REV_MSG_GOV_NOT_COMMUNITY):
        #                 print(
        #                     "        REV_MSG_GOV_NOT_COMMUNITY _enableCommunityGuard",
        #                     st_sender,
        #                 )
        #                 self.v.enableCommunityGuard({"from": st_sender})
        #         # Always enable
        #         print("                    rule_enableCommunityGuard", st_sender)
        #         self.v.enableCommunityGuard({"from": self.communityKey})
        #         self.communityGuardDisabled = False
        #     else:
        #         print(
        #             "        REV_MSG_GOV_ENABLED_GUARD _enableCommunityGuard", st_sender
        #         )
        #         with reverts(REV_MSG_GOV_ENABLED_GUARD):
        #             self.v.enableCommunityGuard({"from": self.communityKey})

        # # Disable community Guard
        # def rule_disableCommunityGuard(self, st_sender):
        #     if not self.communityGuardDisabled:
        #         if st_sender != self.communityKey:
        #             with reverts(REV_MSG_GOV_NOT_COMMUNITY):
        #                 self.v.disableCommunityGuard({"from": st_sender})
        #         # Always disable
        #         print("                    rule_disableCommunityGuard", st_sender)
        #         self.v.disableCommunityGuard({"from": self.communityKey})
        #         self.communityGuardDisabled = True
        #     else:
        #         print(
        #             "        REV_MSG_GOV_DISABLED_GUARD _disableCommunityGuard",
        #             st_sender,
        #         )
        #         with reverts(REV_MSG_GOV_DISABLED_GUARD):
        #             self.v.disableCommunityGuard({"from": self.communityKey})

        # # Governance attemps to withdraw FLIP in case of emergency
        # def rule_govWithdrawal(self, st_sender):
        #     # Withdraw token A and token B - not native to make the checking easier due to gas expenditure
        #     tokenstoWithdraw = self.tokensList[1:]
        #     if self.communityGuardDisabled:
        #         if st_sender != self.governor:
        #             with reverts(REV_MSG_GOV_GOVERNOR):
        #                 self.v.govWithdraw(tokenstoWithdraw, {"from": st_sender})

        #         if self.suspended:
        #             if (
        #                 getChainTime() - self.km.getLastValidateTime()
        #                 < AGG_KEY_EMERGENCY_TIMEOUT
        #             ):
        #                 print("        REV_MSG_VAULT_DELAY _govWithdrawal")
        #                 with reverts(REV_MSG_VAULT_DELAY):
        #                     self.v.govWithdraw(
        #                         tokenstoWithdraw, {"from": self.governor}
        #                     )
        #             else:
        #                 governorBals = {
        #                     token: token.balanceOf(self.governor)
        #                     for token in tokenstoWithdraw
        #                 }
        #                 vaultBals = {
        #                     token: token.balanceOf(self.v) for token in tokenstoWithdraw
        #                 }
        #                 print("                    rule_govWithdrawal", st_sender)
        #                 self.v.govWithdraw(tokenstoWithdraw, {"from": self.governor})
        #                 # Governor has all the tokens - do the checking and return the tokens for the invariant check
        #                 for token in tokenstoWithdraw:
        #                     assert (
        #                         token.balanceOf(self.governor)
        #                         == governorBals[token] + vaultBals[token]
        #                     )
        #                     assert token.balanceOf(self.v) == 0
        #                     token.transfer(
        #                         self.v, vaultBals[token], {"from": self.governor}
        #                     )
        #         else:
        #             print("        REV_MSG_GOV_NOT_SUSPENDED _govWithdrawal")
        #             with reverts(REV_MSG_GOV_NOT_SUSPENDED):
        #                 self.v.govWithdraw(tokenstoWithdraw, {"from": self.governor})
        #     else:
        #         print("        REV_MSG_GOV_ENABLED_GUARD _govWithdrawal")
        #         with reverts(REV_MSG_GOV_ENABLED_GUARD):
        #             self.v.govWithdraw(tokenstoWithdraw, {"from": self.governor})

        # # Enable swaps if they are disabled
        # def rule_enableSwaps(self, st_sender):
        #     if not self.swapsEnabled:
        #         if st_sender != self.governor:
        #             with reverts(REV_MSG_GOV_GOVERNOR):
        #                 print("        REV_MSG_GOV_GOVERNOR _enableSwaps", st_sender)
        #                 self.v.enableSwaps({"from": st_sender})
        #         # Always enable
        #         print("                    rule_enableSwaps", st_sender)
        #         self.v.enableSwaps({"from": self.governor})
        #         self.swapsEnabled = True
        #     else:
        #         print("        REV_MSG_VAULT_SWAPS_EN _enableSwaps", st_sender)
        #         with reverts(REV_MSG_VAULT_SWAPS_EN):
        #             self.v.enableSwaps({"from": self.governor})

        # # Disable swaps if they are enabled (only 1/5 times)
        # def rule_disableSwaps(self, st_sender):
        #     if self.swapsEnabled:
        #         if st_sender != self.governor:
        #             with reverts(REV_MSG_GOV_GOVERNOR):
        #                 print("        REV_MSG_GOV_GOVERNOR _disableSwaps", st_sender)
        #                 self.v.disableSwaps({"from": st_sender})
        #         else:
        #             print("                    rule_disableSwaps", st_sender)
        #             self.v.disableSwaps({"from": st_sender})
        #             self.swapsEnabled = False
        #     else:
        #         print(
        #             "        REV_MSG_GOV_DISABLED_GUARD _disableSwaps",
        #             st_sender,
        #         )
        #         with reverts(REV_MSG_VAULT_SWAPS_DIS):
        #             self.v.disableSwaps({"from": self.governor})

        # # Swap NATIVE
        # def rule_swapNative(
        #     self, st_sender, st_egressParams, st_egressReceiver, st_native_amount
        # ):
        #     args = (st_egressParams, st_egressReceiver)
        #     toLog = (*args, st_sender)
        #     if self.suspended:
        #         with reverts(REV_MSG_GOV_SUSPENDED):
        #             print(
        #                 "        REV_MSG_GOV_SUSPENDED _swapNative",
        #             )
        #             self.v.swapNative(*args, {"from": st_sender})
        #     else:
        #         if self.swapsEnabled:
        #             if st_native_amount == 0:
        #                 print("        REV_MSG_NZ_UINT _swapNative", *toLog)
        #                 with reverts(REV_MSG_NZ_UINT):
        #                     self.v.swapNative(
        #                         *args,
        #                         {"from": st_sender, "amount": st_native_amount},
        #                     )
        #             else:
        #                 if web3.eth.get_balance(str(st_sender)) >= st_native_amount:
        #                     print("                    rule_swapNative", *toLog)
        #                     tx = self.v.swapNative(
        #                         *args,
        #                         {"from": st_sender, "amount": st_native_amount},
        #                     )
        #                     assert (
        #                         web3.eth.get_balance(self.v.address)
        #                         == self.nativeBals[self.v.address] + st_native_amount
        #                     )
        #                     self.nativeBals[self.v.address] += st_native_amount
        #                     self.nativeBals[st_sender] -= st_native_amount
        #                     assert tx.events["SwapNative"]["amount"] == st_native_amount
        #                     assert (
        #                         tx.events["SwapNative"]["egressParams"]
        #                         == st_egressParams
        #                     )
        #                     assert tx.events["SwapNative"][
        #                         "egressReceiver"
        #                     ] == "0x" + cleanHexStr(st_egressReceiver)

        # # Swap Token
        # def rule_swapToken(
        #     self,
        #     st_sender,
        #     st_egressParams,
        #     st_egressReceiver,
        #     st_token_amount,
        #     st_token,
        # ):
        #     args = (st_egressParams, st_egressReceiver, st_token, st_token_amount)
        #     toLog = (*args, st_sender)
        #     if self.suspended:
        #         with reverts(REV_MSG_GOV_SUSPENDED):
        #             print("        REV_MSG_GOV_SUSPENDED _swapToken")
        #             self.v.swapToken(
        #                 *args,
        #                 {"from": st_sender},
        #             )
        #     else:
        #         if self.swapsEnabled:
        #             if st_token_amount == 0:
        #                 print("        REV_MSG_NZ_UINT _swapToken", *toLog)
        #                 with reverts(REV_MSG_NZ_UINT):
        #                     self.v.swapToken(
        #                         *args,
        #                         {"from": st_sender},
        #                     )
        #             else:
        #                 st_token.approve(self.v, st_token_amount, {"from": st_sender})
        #                 if st_token.balanceOf(st_sender) < st_token_amount:
        #                     print("        REV_MSG_ERC20_EXCEED_BAL _swapToken", *toLog)
        #                     with reverts(REV_MSG_ERC20_EXCEED_BAL):
        #                         self.v.swapToken(
        #                             *args,
        #                             {"from": st_sender},
        #                         )
        #                 else:
        #                     print("                    rule_swapToken", *toLog)
        #                     tx = self.v.swapToken(
        #                         *args,
        #                         {"from": st_sender},
        #                     )

        #                     if st_token == self.tokenA:
        #                         assert (
        #                             st_token.balanceOf(self.v.address)
        #                             == self.tokenABals[self.v.address] + st_token_amount
        #                         )
        #                         self.tokenABals[self.v.address] += st_token_amount
        #                         self.tokenABals[st_sender] -= st_token_amount
        #                     elif st_token == self.tokenB:
        #                         assert (
        #                             st_token.balanceOf(self.v.address)
        #                             == self.tokenBBals[self.v.address] + st_token_amount
        #                         )
        #                         self.tokenBBals[self.v.address] += st_token_amount
        #                         self.tokenBBals[st_sender] -= st_token_amount
        #                     else:
        #                         assert False, "Panicc"

        #                     assert tx.events["SwapToken"]["amount"] == st_token_amount
        #                     assert (
        #                         tx.events["SwapToken"]["egressParams"]
        #                         == st_egressParams
        #                     )
        #                     assert tx.events["SwapToken"][
        #                         "egressReceiver"
        #                     ] == "0x" + cleanHexStr(st_egressReceiver)
        #                     assert (
        #                         tx.events["SwapToken"]["ingressToken"]
        #                         == st_token.address
        #                     )

        # Check all the balances of every address are as they should be after every tx
        def invariant_bals(self):
            self.numTxsTested += 1
            for addr in self.allAddrs:
                assert web3.eth.get_balance(addr) == self.nativeBals[
                    addr
                ] - calculateGasSpentByAddress(addr, self.iniTransactionNumber[addr])
                assert self.tokenA.balanceOf(addr) == self.tokenABals[addr]
                assert self.tokenB.balanceOf(addr) == self.tokenBBals[addr]

        # Check variable(s) after every tx that shouldn't change since there's
        # no intentional way to
        def invariant_keys(self):
            assert self.v.getKeyManager() == self.km.address
            assert self.v.getGovernor() == self.governor
            assert self.v.getCommunityKey() == self.communityKey

        # Check the state variables after every tx
        def invariant_state_vars(self):
            assert self.communityGuardDisabled == self.v.getCommunityGuardDisabled()
            assert self.suspended == self.v.getSuspendedState()
            assert self.swapsEnabled == self.v.getSwapsEnabled()

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f"Total rules executed = {self.numTxsTested-1}")

    state_machine(StateMachine, a, cfDeploy, Deposit, Token, settings=settings)
