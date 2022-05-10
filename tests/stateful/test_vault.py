from ctypes import addressof
from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy, contract_strategy
from hypothesis import strategies as hypStrat
from random import choice, choices
import time

settings = {"stateful_step_count": 100, "max_examples": 50}


# Stateful test for all functions in the Vault
def test_vault(
    BaseStateMachine, state_machine, a, cfDeploy, DepositEth, DepositToken, Token
):

    # The max swapID to use. SwapID is needed as a salt to create a unique create2
    # address, and for ease they're used between 1 and MAX_SWAPID inclusive in this test
    # (since 0 will cause a revert when fetching).
    MAX_SWAPID = 5
    # The max number of addresses to send txs from. This is used both for simulating
    # users where ETH/tokens come out of their account (send ETH/tokens), and also for
    # being the sender of fcns where the sender shouldn't matter, but just needs a
    # sender (fcns that require an aggKey sig like `transfer` and `fetchDepositEth`).
    MAX_NUM_SENDERS = 5
    # The max amount of ETH for a 'user' to send to a deposit address, so that
    # the same user can send many more times without running out
    MAX_ETH_SEND = E_18
    # The max amount of tokens for a 'user' to send to a deposit address, so that
    # the same user can send many more times without running out
    MAX_TOKEN_SEND = 10**5 * E_18
    # The max amount of tokens for a 'user' to send to a deposit address, so that
    # the same user can send many more times without running out
    INIT_TOKEN_AMNT = MAX_TOKEN_SEND * 100

    class StateMachine(BaseStateMachine):

        """
        This test calls functions from Vault in random orders. It uses a set number of DepositEth
        and DepositToken contracts/create2 addresses for ETH & each token (MAX_SWAPID amount of each,
        3 * MAX_SWAPID total) and also randomly sends ETH and the 2 ERC20 tokens to the create2
        addresses that correspond to the create2 addresses so that something can actually be fetched
        and transferred.
        The parameters used are so that they're small enough to increase the likelihood of the same
        address being used in multiple interactions (e.g. 2  x transfers then a fetch etc) and large
        enough to ensure there's variety in them
        """

        # Set up the initial test conditions once
        def __init__(cls, a, cfDeploy, DepositEth, DepositToken, Token):
            # cls.aaa = {addr: addr for addr, addr in enumerate(a)}
            super().__init__(cls, a, cfDeploy)

            cls.tokenA = a[0].deploy(
                Token, "NotAPonziA", "NAPA", INIT_TOKEN_SUPPLY * 10
            )
            cls.tokenB = a[0].deploy(
                Token, "NotAPonziB", "NAPB", INIT_TOKEN_SUPPLY * 10
            )
            cls.tokensList = (ETH_ADDR, cls.tokenA, cls.tokenB)

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
                getCreate2Addr(cls.v.address, cleanHexStrPad(swapID), DepositEth, "")
                for swapID in range(1, MAX_SWAPID + 1)
            ]
            cls.create2TokenAAddrs = [
                getCreate2Addr(
                    cls.v.address,
                    cleanHexStrPad(swapID),
                    DepositToken,
                    cleanHexStrPad(cls.tokenA.address),
                )
                for swapID in range(1, MAX_SWAPID + 1)
            ]
            cls.create2TokenBAddrs = [
                getCreate2Addr(
                    cls.v.address,
                    cleanHexStrPad(swapID),
                    DepositToken,
                    cleanHexStrPad(cls.tokenB.address),
                )
                for swapID in range(1, MAX_SWAPID + 1)
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
            self.ethBals = {
                # Accounts within "a" will have INIT_ETH_BAL - gas spent in setup/deployment
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

            self.current_communityKey = self.v.getCommunityKey()
            self.communityGuardDisabled = self.v.getCommunityGuard()
            self.suspended = self.v.getSuspendedState()

        # Variables that will be a random value with each fcn/rule called

        st_eth_amount = strategy("uint", max_value=MAX_ETH_SEND)
        st_eth_amounts = strategy("uint[]", max_value=MAX_ETH_SEND)
        st_token = contract_strategy("Token")
        st_tokens = hypStrat.lists(st_token)
        st_token_amount = strategy("uint", max_value=MAX_TOKEN_SEND)
        st_swapID = strategy("uint", max_value=MAX_SWAPID)
        st_swapIDs = strategy("uint[]", min_value=1, max_value=MAX_SWAPID, unique=True)
        # Only want the 1st 5 addresses so that the chances of multiple
        # txs occurring from the same address is greatly increased while still
        # ensuring diversity in senders
        st_sender = strategy("address", length=MAX_NUM_SENDERS)
        st_sender_any = strategy("address")
        st_recip = strategy("address", length=MAX_NUM_SENDERS)
        st_recips = strategy("address[]", length=MAX_NUM_SENDERS, unique=True)

        def rule_allBatch(self, st_swapIDs, st_recips, st_eth_amounts, st_sender):
            fetchTokens = choices(self.tokensList, k=len(st_swapIDs))
            fetchEthTotal = sum(
                self.ethBals[
                    getCreate2Addr(
                        self.v.address, cleanHexStrPad(st_swapIDs[i]), DepositEth, ""
                    )
                ]
                for i, x in enumerate(fetchTokens)
                if x == ETH_ADDR
            )
            fetchTokenATotal = sum(
                self.tokenABals[
                    getCreate2Addr(
                        self.v.address,
                        cleanHexStrPad(st_swapIDs[i]),
                        DepositToken,
                        cleanHexStrPad(self.tokenA.address),
                    )
                ]
                for i, x in enumerate(fetchTokens)
                if x == self.tokenA
            )
            fetchTokenBTotal = sum(
                self.tokenBBals[
                    getCreate2Addr(
                        self.v.address,
                        cleanHexStrPad(st_swapIDs[i]),
                        DepositToken,
                        cleanHexStrPad(self.tokenB.address),
                    )
                ]
                for i, x in enumerate(fetchTokens)
                if x == self.tokenB
            )

            tranMinLen = trimToShortest([st_recips, st_eth_amounts])
            tranTokens = choices(self.tokensList, k=tranMinLen)
            tranTotals = {
                tok: sum(
                    [st_eth_amounts[i] for i, x in enumerate(tranTokens) if x == tok]
                )
                for tok in self.tokensList
            }
            validEthIdxs = getValidTranIdxs(
                tranTokens,
                st_eth_amounts,
                self.ethBals[self.v.address] + fetchEthTotal,
                ETH_ADDR,
            )
            tranTotals[ETH_ADDR] = sum(
                [
                    st_eth_amounts[i]
                    for i, x in enumerate(tranTokens)
                    if x == ETH_ADDR and i in validEthIdxs
                ]
            )

            callDataNoSig = self.v.allBatch.encode_input(
                agg_null_sig(self.km.address, chain.id),
                st_swapIDs,
                fetchTokens,
                tranTokens,
                st_recips,
                st_eth_amounts,
            )

            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _allBatch")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.v.allBatch(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        st_swapIDs,
                        fetchTokens,
                        tranTokens,
                        st_recips,
                        st_eth_amounts,
                        {"from": st_sender},
                    )
            elif (
                tranTotals[self.tokenA] - fetchTokenATotal
                > self.tokenABals[self.v.address]
                or tranTotals[self.tokenB] - fetchTokenBTotal
                > self.tokenBBals[self.v.address]
            ):
                print(
                    "        NOT ENOUGH TOKENS IN VAULT rule_allBatch",
                    st_swapIDs,
                    fetchTokens,
                    tranTotals,
                    st_recips,
                    st_eth_amounts,
                    st_sender,
                )
                with reverts():
                    self.v.allBatch(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        st_swapIDs,
                        fetchTokens,
                        tranTokens,
                        st_recips,
                        st_eth_amounts,
                    )
            else:
                print(
                    "                    rule_allBatch",
                    st_swapIDs,
                    fetchTokens,
                    tranTokens,
                    st_recips,
                    st_eth_amounts,
                    st_sender,
                )
                tx = self.v.allBatch(
                    AGG_SIGNER_1.getSigDataWithNonces(
                        callDataNoSig, nonces, AGG, self.km.address
                    ),
                    st_swapIDs,
                    fetchTokens,
                    tranTokens,
                    st_recips,
                    st_eth_amounts,
                    {"from": st_sender},
                )

                # Alter bals from the fetches
                for swapID, tok in zip(st_swapIDs, fetchTokens):
                    if tok == ETH_ADDR:
                        addr = getCreate2Addr(
                            self.v.address, cleanHexStrPad(swapID), DepositEth, ""
                        )
                        self.ethBals[self.v.address] += self.ethBals[addr]
                        self.ethBals[addr] = 0
                    else:
                        addr = getCreate2Addr(
                            self.v.address,
                            cleanHexStrPad(swapID),
                            DepositToken,
                            cleanHexStrPad(tok.address),
                        )
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
                    zip(tranTokens, st_recips, st_eth_amounts)
                ):
                    if tok == ETH_ADDR:
                        if i in validEthIdxs:
                            self.ethBals[rec] += am
                            self.ethBals[self.v.address] -= am
                    elif tok == self.tokenA:
                        self.tokenABals[rec] += am
                        self.tokenABals[self.v.address] -= am
                    elif tok == self.tokenB:
                        self.tokenBBals[rec] += am
                        self.tokenBBals[self.v.address] -= am
                    else:
                        assert False, "Panic"

        # Transfers ETH or tokens out the vault. Want this to be called by rule_vault_transfer_eth
        # etc individually and not directly since they're all the same just with a different tokenAddr
        # input
        def _vault_transfer(self, bals, tokenAddr, st_sender, st_recip, st_eth_amount):
            callDataNoSig = self.v.transfer.encode_input(
                agg_null_sig(self.km.address, chain.id),
                tokenAddr,
                st_recip,
                st_eth_amount,
            )

            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _vault_transfer")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.v.transfer(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        tokenAddr,
                        st_recip,
                        st_eth_amount,
                        {"from": st_sender},
                    )
            elif st_eth_amount == 0:
                print(
                    "        REV_MSG_NZ_UINT _vault_transfer",
                    tokenAddr,
                    st_sender,
                    st_recip,
                    st_eth_amount,
                )
                with reverts(REV_MSG_NZ_UINT):
                    self.v.transfer(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        tokenAddr,
                        st_recip,
                        st_eth_amount,
                        {"from": st_sender},
                    )
            elif bals[self.v.address] < st_eth_amount and tokenAddr != ETH_ADDR:
                print(
                    "        NOT ENOUGH TOKENS IN VAULT _vault_transfer",
                    tokenAddr,
                    st_sender,
                    st_recip,
                    st_eth_amount,
                )
                with reverts():
                    self.v.transfer(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        tokenAddr,
                        st_recip,
                        st_eth_amount,
                        {"from": st_sender},
                    )
            else:
                print(
                    "                    _vault_transfer",
                    tokenAddr,
                    st_sender,
                    st_recip,
                    st_eth_amount,
                )
                self.v.transfer(
                    AGG_SIGNER_1.getSigDataWithNonces(
                        callDataNoSig, nonces, AGG, self.km.address
                    ),
                    tokenAddr,
                    st_recip,
                    st_eth_amount,
                    {"from": st_sender},
                )

                if bals[self.v.address] >= st_eth_amount or tokenAddr != ETH_ADDR:
                    bals[self.v.address] -= st_eth_amount
                    bals[st_recip] += st_eth_amount

        def rule_vault_transfer_eth(self, st_sender, st_recip, st_eth_amount):
            self._vault_transfer(
                self.ethBals, ETH_ADDR, st_sender, st_recip, st_eth_amount
            )

        def rule_vault_transfer_tokenA(self, st_sender, st_recip, st_token_amount):
            self._vault_transfer(
                self.tokenABals, self.tokenA, st_sender, st_recip, st_token_amount
            )

        def rule_vault_transfer_tokenB(self, st_sender, st_recip, st_token_amount):
            self._vault_transfer(
                self.tokenBBals, self.tokenB, st_sender, st_recip, st_token_amount
            )

        # Send any combination of eth/tokenA/tokenB out of the vault. Using st_eth_amounts
        # for both eth amounts and token amounts here because its max is within the bounds of
        # both eth and tokens.
        def rule_vault_transferBatch(self, st_sender, st_recips, st_eth_amounts):
            minLen = trimToShortest([st_recips, st_eth_amounts])
            tokens = choices(self.tokensList, k=minLen)
            tranTotals = {
                tok: sum([st_eth_amounts[i] for i, x in enumerate(tokens) if x == tok])
                for tok in self.tokensList
            }
            validEthIdxs = getValidTranIdxs(
                tokens, st_eth_amounts, self.ethBals[self.v.address], ETH_ADDR
            )
            tranTotals[ETH_ADDR] = sum(
                [
                    st_eth_amounts[i]
                    for i, x in enumerate(tokens)
                    if x == ETH_ADDR and i in validEthIdxs
                ]
            )

            callDataNoSig = self.v.transferBatch.encode_input(
                agg_null_sig(self.km.address, chain.id),
                tokens,
                st_recips,
                st_eth_amounts,
            )

            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _vault_transferBatch")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.v.transferBatch(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        tokens,
                        st_recips,
                        st_eth_amounts,
                    )
            elif (
                tranTotals[self.tokenA] > self.tokenABals[self.v.address]
                or tranTotals[self.tokenB] > self.tokenBBals[self.v.address]
            ):
                print(
                    "        NOT ENOUGH TOKENS IN VAULT rule_vault_transferBatch",
                    st_sender,
                    tokens,
                    st_recips,
                    st_eth_amounts,
                )
                with reverts():
                    self.v.transferBatch(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        tokens,
                        st_recips,
                        st_eth_amounts,
                    )
            else:
                print(
                    "                    rule_vault_transferBatch",
                    st_sender,
                    tokens,
                    st_recips,
                    st_eth_amounts,
                )
                self.v.transferBatch(
                    AGG_SIGNER_1.getSigDataWithNonces(
                        callDataNoSig, nonces, AGG, self.km.address
                    ),
                    tokens,
                    st_recips,
                    st_eth_amounts,
                )

                for i in range(len(st_recips)):
                    if tokens[i] == ETH_ADDR:
                        if i in validEthIdxs:
                            self.ethBals[st_recips[i]] += st_eth_amounts[i]
                            self.ethBals[self.v.address] -= st_eth_amounts[i]
                    elif tokens[i] == self.tokenA:
                        self.tokenABals[st_recips[i]] += st_eth_amounts[i]
                        self.tokenABals[self.v.address] -= st_eth_amounts[i]
                    elif tokens[i] == self.tokenB:
                        self.tokenBBals[st_recips[i]] += st_eth_amounts[i]
                        self.tokenBBals[self.v.address] -= st_eth_amounts[i]
                    else:
                        assert False, "Panic"

        # Transfers ETH from a user/sender to one of the depositEth create2 addresses
        def rule_transfer_eth_to_depositEth(self, st_sender, st_swapID, st_eth_amount):
            # Since st_swapID = 0 won't be able to be fetched (reverts on empty input),
            # no point sending ETH to that corresponding addr
            if st_swapID != 0 and self.ethBals[st_sender] >= st_eth_amount:
                print(
                    "                    rule_transfer_eth_to_depositEth",
                    st_sender,
                    st_swapID,
                    st_eth_amount,
                )
                depositAddr = getCreate2Addr(
                    self.v.address, cleanHexStrPad(st_swapID), DepositEth, ""
                )
                st_sender.transfer(depositAddr, st_eth_amount)

                self.ethBals[st_sender] -= st_eth_amount
                self.ethBals[depositAddr] += st_eth_amount

        # Transfers a token from a user/sender to one of the depositEth create2 addresses.
        # This isn't called directly since rule_transfer_tokens_to_depositTokenA etc use it
        # in the same way but with a different tokenAddr
        def _transfer_tokens_to_depositToken(
            self, bals, token, st_sender, st_swapID, st_token_amount
        ):
            # Since st_swapID = 0 won't be able to be fetched (reverts on empty input),
            # no point sending ETH to that corresponding addr
            if st_swapID != 0 and bals[st_sender] >= st_token_amount:
                print(
                    "                    _transfer_tokens_to_depositToken",
                    token,
                    st_sender,
                    st_swapID,
                    st_token_amount,
                )
                depositAddr = getCreate2Addr(
                    self.v.address,
                    cleanHexStrPad(st_swapID),
                    DepositToken,
                    cleanHexStrPad(token.address),
                )
                token.transfer(depositAddr, st_token_amount, {"from": st_sender})

                bals[st_sender] -= st_token_amount
                bals[depositAddr] += st_token_amount

        # Deposits tokenA from a user to a tokenA create2
        def rule_transfer_tokens_to_depositTokenA(
            self, st_sender, st_swapID, st_token_amount
        ):
            self._transfer_tokens_to_depositToken(
                self.tokenABals, self.tokenA, st_sender, st_swapID, st_token_amount
            )

        # Deposits tokenB from a user to a tokenB create2
        def rule_transfer_tokens_to_depositTokenB(
            self, st_sender, st_swapID, st_token_amount
        ):
            self._transfer_tokens_to_depositToken(
                self.tokenBBals, self.tokenB, st_sender, st_swapID, st_token_amount
            )

        # Fetch the ETH deposit of a random create2
        def rule_fetchDepositEth(self, st_sender, st_swapID):
            callDataNoSig = self.v.fetchDepositEth.encode_input(
                agg_null_sig(self.km.address, chain.id), st_swapID
            )

            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _fetchDepositEth")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.v.fetchDepositEth(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        st_swapID,
                    )
            elif st_swapID == 0:
                print(
                    "        REV_MSG_NZ_BYTES32 rule_fetchDepositEth",
                    st_sender,
                    st_swapID,
                )
                with reverts(REV_MSG_NZ_BYTES32):
                    self.v.fetchDepositEth(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        st_swapID,
                    )
            else:
                print("                    rule_fetchDepositEth", st_sender, st_swapID)
                self.v.fetchDepositEth(
                    AGG_SIGNER_1.getSigDataWithNonces(
                        callDataNoSig, nonces, AGG, self.km.address
                    ),
                    st_swapID,
                )

                depositAddr = getCreate2Addr(
                    self.v.address, cleanHexStrPad(st_swapID), DepositEth, ""
                )
                depositBal = self.ethBals[depositAddr]
                self.ethBals[depositAddr] -= depositBal
                self.ethBals[self.v.address] += depositBal

        def rule_fetchDepositEthBatch(self, st_sender, st_swapIDs):
            addrs = [
                getCreate2Addr(self.v.address, cleanHexStrPad(swapID), DepositEth, "")
                for swapID in st_swapIDs
            ]
            total = sum([web3.eth.get_balance(addr) for addr in addrs])

            callDataNoSig = self.v.fetchDepositEthBatch.encode_input(
                agg_null_sig(self.km.address, chain.id), st_swapIDs
            )
            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _fetchDepositEthBatch")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.v.fetchDepositEthBatch(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        st_swapIDs,
                    )
                return
            print(
                "                    rule_fetchDepositEthBatch", st_sender, st_swapIDs
            )
            self.v.fetchDepositEthBatch(
                AGG_SIGNER_1.getSigDataWithNonces(
                    callDataNoSig, nonces, AGG, self.km.address
                ),
                st_swapIDs,
            )

            for addr in addrs:
                self.ethBals[addr] = 0
            self.ethBals[self.v.address] += total

        # Fetch the token deposit of a random create2
        def _fetchDepositToken(self, bals, token, st_sender, st_swapID):
            callDataNoSig = self.v.fetchDepositToken.encode_input(
                agg_null_sig(self.km.address, chain.id), st_swapID, token
            )

            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _fetchDepositToken")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.v.fetchDepositToken(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        st_swapID,
                        token,
                    )
            elif st_swapID == 0:
                print(
                    "        REV_MSG_NZ_BYTES32 _fetchDepositToken",
                    token.address,
                    st_sender,
                    st_swapID,
                )
                with reverts(REV_MSG_NZ_BYTES32):
                    self.v.fetchDepositToken(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        st_swapID,
                        token,
                    )
            else:
                print(
                    "                    _fetchDepositToken",
                    token,
                    st_sender,
                    st_swapID,
                )
                self.v.fetchDepositToken(
                    AGG_SIGNER_1.getSigDataWithNonces(
                        callDataNoSig, nonces, AGG, self.km.address
                    ),
                    st_swapID,
                    token,
                )

                depositAddr = getCreate2Addr(
                    self.v.address,
                    cleanHexStrPad(st_swapID),
                    DepositToken,
                    cleanHexStrPad(token.address),
                )
                depositBal = bals[depositAddr]
                bals[depositAddr] -= depositBal
                bals[self.v.address] += depositBal

        # Fetch the tokenA deposit of a random create2
        def rule_fetchDepositToken_tokenA(self, st_sender, st_swapID):
            self._fetchDepositToken(self.tokenABals, self.tokenA, st_sender, st_swapID)

        # Fetch the tokenB deposit of a random create2
        def rule_fetchDepositToken_tokenB(self, st_sender, st_swapID):
            self._fetchDepositToken(self.tokenBBals, self.tokenB, st_sender, st_swapID)

        # Fetches random tokens from random swapID. Since there's no real way
        # to get the lengths of the input arrays to be the same most of the time, I'm going to have to
        # use a random number to determine whether or not to concat all arrays to the
        # length of the shortest so that we'll get mostly valid txs and maximise usefulness. The
        # easiest random num to use is the length of the arrays themselves - I'm gonna use '3' as the
        # magic shortest length that should trigger not concating for no particular reason
        def rule_fetchDepositTokenBatch(self, st_sender, st_swapIDs, st_tokens):
            minLen = min(map(len, [st_swapIDs, st_tokens]))
            maxLen = max(map(len, [st_swapIDs, st_tokens]))

            callDataNoSig = self.v.fetchDepositTokenBatch.encode_input(
                agg_null_sig(self.km.address, chain.id), st_swapIDs, st_tokens
            )
            if self.suspended:
                print("        REV_MSG_GOV_SUSPENDED _fetchDepositToken")
                with reverts(REV_MSG_GOV_SUSPENDED):
                    self.v.fetchDepositTokenBatch(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        st_swapIDs,
                        st_tokens,
                    )
            elif minLen == 3 and minLen != maxLen:
                callDataNoSig = self.v.fetchDepositTokenBatch.encode_input(
                    agg_null_sig(self.km.address, chain.id), st_swapIDs, st_tokens
                )
                print(
                    "        rule_fetchDepositTokenBatch",
                    st_sender,
                    st_swapIDs,
                    st_tokens,
                )
                with reverts(REV_MSG_V_ARR_LEN):
                    self.v.fetchDepositTokenBatch(
                        AGG_SIGNER_1.getSigDataWithNonces(
                            callDataNoSig, nonces, AGG, self.km.address
                        ),
                        st_swapIDs,
                        st_tokens,
                    )
            else:
                trimToShortest([st_swapIDs, st_tokens])
                callDataNoSig = self.v.fetchDepositTokenBatch.encode_input(
                    agg_null_sig(self.km.address, chain.id), st_swapIDs, st_tokens
                )

                print(
                    "                    rule_fetchDepositTokenBatch",
                    st_sender,
                    st_swapIDs,
                    st_tokens,
                )
                self.v.fetchDepositTokenBatch(
                    AGG_SIGNER_1.getSigDataWithNonces(
                        callDataNoSig, nonces, AGG, self.km.address
                    ),
                    st_swapIDs,
                    st_tokens,
                )

                for swapID, token in zip(st_swapIDs, st_tokens):
                    addr = getCreate2Addr(
                        self.v.address,
                        cleanHexStrPad(swapID),
                        DepositToken,
                        cleanHexStrPad(token.address),
                    )
                    if token == self.tokenA:
                        self.tokenABals[self.v.address] += self.tokenABals[addr]
                        self.tokenABals[addr] = 0
                    elif token == self.tokenB:
                        self.tokenBBals[self.v.address] += self.tokenBBals[addr]
                        self.tokenBBals[addr] = 0
                    else:
                        assert False, "Panicc"

        # Sleep AGG_KEY_EMERGENCY_TIMEOUT
        def rule_sleep_14_days(self):
            print("                    rule_sleep_14_days")
            chain.sleep(AGG_KEY_EMERGENCY_TIMEOUT)

        # Suspends the stake Manager if st_sender matches the governor address. It has
        # has a 1/20 chance of being the governor - don't want to suspend it too often.
        def rule_suspend(self, st_sender_any):
            if st_sender_any == self.governor:
                if self.suspended:
                    print("        REV_MSG_GOV_SUSPENDED _suspend")
                    with reverts(REV_MSG_GOV_SUSPENDED):
                        self.v.suspend({"from": st_sender_any})
                else:
                    print("                    rule_suspend", st_sender_any)
                    self.v.suspend({"from": st_sender_any})
                    self.suspended = True
            else:
                print("        REV_MSG_GOV_GOVERNOR _suspend")
                with reverts(REV_MSG_GOV_GOVERNOR):
                    self.v.suspend({"from": st_sender_any})

        # Resumes the stake Manager if it is suspended. We always resume it to avoid
        # having the stakeManager suspended too often
        def rule_resume(self, st_sender):
            if self.suspended:
                if st_sender != self.governor:
                    with reverts(REV_MSG_GOV_GOVERNOR):
                        self.v.resume({"from": st_sender})
                # Always resume
                print("                    rule_resume", st_sender)
                self.v.resume({"from": self.governor})
                self.suspended = False
            else:
                print("        REV_MSG_GOV_NOT_SUSPENDED _resume", st_sender)
                with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                    self.v.resume({"from": self.governor})

        # Updates community Key - happens with low probability - 1/20
        def rule_setCommKeyWithCommKey(self, st_sender):
            newCommunityKey = choice([self.communityKey, self.communityKey_2])
            if st_sender == self.current_communityKey:
                print("                    rule_setCommKeyWithCommKey", st_sender)
                self.v.setCommKeyWithCommKey(newCommunityKey, {"from": st_sender})
                self.current_communityKey = newCommunityKey
            else:
                print(
                    "        REV_MSG_GOV_NOT_COMMUNITY _setCommKeyWithCommKey",
                    st_sender,
                )
                with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                    self.v.setCommKeyWithCommKey(newCommunityKey, {"from": st_sender})

        # Enable community Guard
        def rule_enableCommunityGuard(self, st_sender):
            if self.communityGuardDisabled:
                if st_sender != self.current_communityKey:
                    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                        self.v.enableCommunityGuard({"from": st_sender})
                # Always enable
                print("                    rule_enableCommunityGuard", st_sender)
                self.v.enableCommunityGuard({"from": self.current_communityKey})
                self.communityGuardDisabled = False
            else:
                print(
                    "        REV_MSG_GOV_ENABLED_GUARD _enableCommunityGuard", st_sender
                )
                with reverts(REV_MSG_GOV_ENABLED_GUARD):
                    self.v.enableCommunityGuard({"from": self.current_communityKey})

        # Enable community Guard
        def rule_disableCommunityGuard(self, st_sender):
            if not self.communityGuardDisabled:
                if st_sender != self.current_communityKey:
                    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
                        self.v.disableCommunityGuard({"from": st_sender})
                # Always disable
                print("                    rule_disableCommunityGuard", st_sender)
                self.v.disableCommunityGuard({"from": self.current_communityKey})
                self.communityGuardDisabled = True
            else:
                print(
                    "        REV_MSG_GOV_DISABLED_GUARD _disableCommunityGuard",
                    st_sender,
                )
                with reverts(REV_MSG_GOV_DISABLED_GUARD):
                    self.v.disableCommunityGuard({"from": self.current_communityKey})

        # Governance attemps to withdraw FLIP in case of emergency
        def rule_govWithdrawal(self, st_sender):
            # Withdraw all tokens - except ETH to make the checking easier due to gas expenditure
            tokenstoWithdraw = self.tokensList[1:]
            if self.communityGuardDisabled:
                if st_sender != self.governor:
                    with reverts(REV_MSG_GOV_GOVERNOR):
                        self.v.govWithdraw(tokenstoWithdraw, {"from": st_sender})

                if self.suspended:
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
                        governorBals = {
                            token: token.balanceOf(self.governor)
                            for token in tokenstoWithdraw
                        }
                        vaultBals = {
                            token: token.balanceOf(self.v) for token in tokenstoWithdraw
                        }
                        print("                    rule_govWithdrawal", st_sender)
                        self.v.govWithdraw(tokenstoWithdraw, {"from": self.governor})
                        # Governor has all the FLIP - do the checking and return the tokens for the invariant check
                        for token in tokenstoWithdraw:
                            assert (
                                token.balanceOf(self.governor)
                                == governorBals[token] + vaultBals[token]
                            )
                            assert token.balanceOf(self.v) == 0
                            token.transfer(
                                self.v, vaultBals[token], {"from": self.governor}
                            )
                else:
                    print("        REV_MSG_GOV_NOT_SUSPENDED _govWithdrawal")
                    with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                        self.v.govWithdraw(tokenstoWithdraw, {"from": self.governor})
            else:
                print("        REV_MSG_GOV_ENABLED_GUARD _govWithdrawal")
                with reverts(REV_MSG_GOV_ENABLED_GUARD):
                    self.v.govWithdraw(tokenstoWithdraw, {"from": self.governor})

        # Check all the balances of every address are as they should be after every tx
        def invariant_bals(self):
            self.numTxsTested += 1
            for addr in self.allAddrs:
                assert web3.eth.get_balance(addr) == self.ethBals[
                    addr
                ] - calculateGasSpentByAddress(addr, self.iniTransactionNumber[addr])
                assert self.tokenA.balanceOf(addr) == self.tokenABals[addr]
                assert self.tokenB.balanceOf(addr) == self.tokenBBals[addr]

        # Check variable(s) after every tx that shouldn't change since there's
        # no intentional way to
        def invariant_nonchangeable(self):
            assert self.v.getKeyManager() == self.km.address

        def invariant_governanceCommunityGuard(self):
            assert self.current_communityKey == self.v.getCommunityKey()
            assert self.communityGuardDisabled == self.v.getCommunityGuard()
            assert self.suspended == self.v.getSuspendedState()

        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f"Total rules executed = {self.numTxsTested-1}")
            # Add time.sleep due to brownie bug that kills virtual machine too quick
            time.sleep(5)

    state_machine(
        StateMachine, a, cfDeploy, DepositEth, DepositToken, Token, settings=settings
    )
