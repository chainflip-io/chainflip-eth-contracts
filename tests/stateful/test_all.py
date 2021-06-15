from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy, contract_strategy
from utils import *
from hypothesis import strategies as hypStrat
from random import choice, choices


settings = {"stateful_step_count": 100, "max_examples": 50}


# Stateful test for all functions in the Vault, KeyManager, and StakeManager
def test_all(BaseStateMachine, state_machine, a, cfDeploy, DepositEth, DepositToken, Token):
    
    # Vault
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
    MAX_TOKEN_SEND = 10**23
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
    MAX_TEST_STAKE = 10**24
    
    class StateMachine(BaseStateMachine):

        """
        This test calls functions Vault, from KeyManager and StakeManager in random orders.

        It uses a set number of DepositEth and DepositToken contracts/create2 addresses 
        for ETH & each token (MAX_SWAPID amount of each, 3 * MAX_SWAPID total) and also 
        randomly sends ETH and the 2 ERC20 tokens to the create2 addresses that 
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
        """

        # Set up the initial test conditions once
        def __init__(cls, a, cfDeploy, DepositEth, DepositToken, Token):
            super().__init__(cls, a, cfDeploy)

            cls.tokenA = a[0].deploy(Token, "NotAPonziA", "NAPA", INIT_TOKEN_SUPPLY)
            cls.tokenB = a[0].deploy(Token, "NotAPonziB", "NAPB", INIT_TOKEN_SUPPLY)
            cls.tokensList = (ETH_ADDR, cls.tokenA, cls.tokenB)

            for token in [cls.tokenA, cls.tokenB]:
                for recip in a[1:]:
                    token.transfer(recip, INIT_TOKEN_AMNT)
            
            cls.create2EthAddrs = [getCreate2Addr(cls.v.address, cleanHexStrPad(swapID), DepositEth, "") for swapID in range(MAX_SWAPID+1)]
            cls.create2TokenAAddrs = [getCreate2Addr(cls.v.address, cleanHexStrPad(swapID), DepositToken, cleanHexStrPad(cls.tokenA.address)) for swapID in range(MAX_SWAPID+1)]
            cls.create2TokenBAddrs = [getCreate2Addr(cls.v.address, cleanHexStrPad(swapID), DepositToken, cleanHexStrPad(cls.tokenB.address)) for swapID in range(MAX_SWAPID+1)]

            cls.stakers = a[:MAX_NUM_SENDERS]

            for staker in cls.stakers:
                cls.f.transfer(staker, INIT_STAKE, {'from': a[0]})
            # Send excess from the deployer to the zero address so that all stakers start
            # with the same balance to make the accounting simpler
            cls.f.transfer("0x0000000000000000000000000000000000000001", cls.f.balanceOf(a[0]) - INIT_STAKE, {'from': a[0]})


        # Reset the local versions of state to compare the contract to after every run
        def setup(self):
            self.allAddrs = self.stakers + [self.sm]
            self.allAddrs = [*[addr.address for addr in self.stakers], *self.create2EthAddrs, 
                *self.create2TokenAAddrs, *self.create2TokenBAddrs, self.v, self.km, self.sm]
            
            callDataNoSig = self.sm.setMinStake.encode_input(gov_null_sig(), INIT_MIN_STAKE)
            tx = self.sm.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), INIT_MIN_STAKE)

            # Vault
            self.ethBals = {addr: INIT_ETH_BAL if addr in a else 0 for addr in self.allAddrs}
            self.tokenABals = {addr: INIT_TOKEN_AMNT if addr in a else 0 for addr in self.allAddrs}
            self.tokenBBals = {addr: INIT_TOKEN_AMNT if addr in a else 0 for addr in self.allAddrs}
            
            # KeyManager
            self.lastValidateTime = tx.timestamp
            self.keyIDToCurKeys = {AGG: AGG_SIGNER_1, GOV: GOV_SIGNER_1}
            self.allKeys = [*self.keyIDToCurKeys.values()] + ([Signer.gen_signer(AGG, nonces)] * int((TOTAL_KEYS - 2)/2)) + ([Signer.gen_signer(GOV, nonces)] * int((TOTAL_KEYS - 2)/2))

            # StakeManager
            self.lastMintBlockNum = self.sm.tx.block_number
            self.emissionPerBlock = EMISSION_PER_BLOCK
            self.totalStake = 0
            self.minStake = INIT_MIN_STAKE
            self.flipBals = {addr: INIT_STAKE if addr in self.stakers else 0 for addr in self.allAddrs}
            self.pendingClaims = {nodeID: NULL_CLAIM for nodeID in range(MAX_NUM_SENDERS + 1)}
            self.numTxsTested = 0


        # Variables that will be a random value with each fcn/rule called

        # Vault

        st_eth_amount = strategy("uint", max_value=MAX_ETH_SEND)
        st_eth_amounts = strategy("uint[]", max_value=MAX_ETH_SEND)
        st_token = contract_strategy('Token')
        st_tokens = hypStrat.lists(st_token)
        st_token_amount = strategy("uint", max_value=MAX_TOKEN_SEND)
        st_swapID = strategy("uint", min_value=1, max_value=MAX_SWAPID)
        st_swapIDs = strategy("uint[]", min_value=1, max_value=MAX_SWAPID, unique=True)
        # Only want the 1st 5 addresses so that the chances of multiple
        # txs occurring from the same address is greatly increased while still
        # ensuring diversity in senders
        st_sender = strategy("address", length=MAX_NUM_SENDERS)
        st_recip = strategy("address", length=MAX_NUM_SENDERS)
        st_recips = strategy("address[]", length=MAX_NUM_SENDERS, unique=True)

        # KeyManager

        st_sig_key_idx = strategy("uint", max_value=TOTAL_KEYS-1)
        st_new_key_idx = strategy("uint", max_value=TOTAL_KEYS-1)
        st_keyID_num = strategy("uint", max_value=len(KEYID_TO_NUM)-1)
        st_msg_data = strategy("bytes")
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)

        # StakeManager

        st_staker = strategy("address", length=MAX_NUM_SENDERS)
        st_returnAddr = strategy("address")
        st_nodeID = strategy("uint", max_value=MAX_NUM_SENDERS)
        st_stake = strategy("uint", max_value=MAX_TEST_STAKE)
        st_expiry_time_diff = strategy("uint", max_value=CLAIM_DELAY*10)
        # This would be 10x the initial supply in 1 year, so is a reasonable max without
        # uint overflowing
        st_emission = strategy("uint", max_value=370 * E_18)
        # In reality this high amount isn't really realistic, but for the sake of testing
        st_minStake = strategy("uint", max_value=int(INIT_STAKE/2))


        # Vault


        def rule_allBatch(self, st_swapIDs, st_recips, st_eth_amounts, st_sender):
            fetchTokens = choices(self.tokensList, k=len(st_swapIDs))
            fetchEthTotal = sum(self.ethBals[getCreate2Addr(self.v.address, cleanHexStrPad(st_swapIDs[i]), DepositEth, "")] for i, x in enumerate(fetchTokens) if x == ETH_ADDR)
            fetchTokenATotal = sum(self.tokenABals[getCreate2Addr(self.v.address, cleanHexStrPad(st_swapIDs[i]), DepositToken, cleanHexStrPad(self.tokenA.address))] for i, x in enumerate(fetchTokens) if x == self.tokenA)
            fetchTokenBTotal = sum(self.tokenBBals[getCreate2Addr(self.v.address, cleanHexStrPad(st_swapIDs[i]), DepositToken, cleanHexStrPad(self.tokenB.address))] for i, x in enumerate(fetchTokens) if x == self.tokenB)

            tranMinLen = trimToShortest([st_recips, st_eth_amounts])
            tranTokens = choices(self.tokensList, k=tranMinLen)
            tranTotals = {tok: sum([st_eth_amounts[i] for i, x in enumerate(tranTokens) if x == tok]) for tok in self.tokensList}

            signer = self._get_key_prob(AGG)
            callDataNoSig = self.v.allBatch.encode_input(agg_null_sig(), st_swapIDs, fetchTokens, tranTokens, st_recips, st_eth_amounts)

            if signer != self.keyIDToCurKeys[AGG]:
                print('        REV_MSG_SIG rule_allBatch', signer, st_swapIDs, fetchTokens, tranTokens, st_recips, st_eth_amounts, st_sender)
                with reverts(REV_MSG_SIG):
                    self.v.allBatch(signer.getSigData(callDataNoSig), st_swapIDs, fetchTokens, tranTokens, st_recips, st_eth_amounts)
            elif tranTotals[ETH_ADDR] - fetchEthTotal > self.ethBals[self.v] or \
            tranTotals[self.tokenA] - fetchTokenATotal > self.tokenABals[self.v] or \
            tranTotals[self.tokenB] - fetchTokenBTotal > self.tokenBBals[self.v]:
                print('        NOT ENOUGH TOKENS IN VAULT rule_allBatch', signer, st_swapIDs, fetchTokens, tranTokens, st_recips, st_eth_amounts, st_sender)
                with reverts():
                    self.v.allBatch(signer.getSigData(callDataNoSig), st_swapIDs, fetchTokens, tranTokens, st_recips, st_eth_amounts)
            else:
                print('                    rule_allBatch', signer, st_swapIDs, fetchTokens, tranTokens, st_recips, st_eth_amounts, st_sender)
                tx = self.v.allBatch(signer.getSigData(callDataNoSig), st_swapIDs, fetchTokens, tranTokens, st_recips, st_eth_amounts, {'from': st_sender})

                self.lastValidateTime = tx.timestamp
                
                # Alter bals from the fetch
                for swapID, tok in zip(st_swapIDs, fetchTokens):
                    if tok == ETH_ADDR:
                        addr = getCreate2Addr(self.v.address, cleanHexStrPad(swapID), DepositEth, "")
                        self.ethBals[self.v] += self.ethBals[addr]
                        self.ethBals[addr] = 0
                    else:
                        addr = getCreate2Addr(self.v.address, cleanHexStrPad(swapID), DepositToken, cleanHexStrPad(tok.address))
                        if tok == self.tokenA:
                            self.tokenABals[self.v] += self.tokenABals[addr]
                            self.tokenABals[addr] = 0
                        elif tok == self.tokenB:
                            self.tokenBBals[self.v] += self.tokenBBals[addr]
                            self.tokenBBals[addr] = 0
                        else:
                            assert False, "Panicc"
                
                # Alter bals from the transfers
                for tok, rec, am in zip(tranTokens, st_recips, st_eth_amounts):
                    if tok == ETH_ADDR:
                        self.ethBals[rec] += am
                        self.ethBals[self.v] -= am
                    elif tok == self.tokenA:
                        self.tokenABals[rec] += am
                        self.tokenABals[self.v] -= am
                    elif tok == self.tokenB:
                        self.tokenBBals[rec] += am
                        self.tokenBBals[self.v] -= am
                    else:
                        assert False, "Panic"
        

        # Transfers ETH or tokens out the vault. Want this to be called by rule_vault_transfer_eth
        # etc individually and not directly since they're all the same just with a different tokenAddr
        # input
        def _vault_transfer(self, bals, tokenAddr, st_sender, st_recip, st_eth_amount):
            callDataNoSig = self.v.transfer.encode_input(agg_null_sig(), tokenAddr, st_recip, st_eth_amount)
            signer = self._get_key_prob(AGG)
            
            if st_eth_amount == 0:
                print('        REV_MSG_NZ_UINT _vault_transfer', tokenAddr, st_sender, st_recip, st_eth_amount, signer)
                with reverts(REV_MSG_NZ_UINT):
                    self.v.transfer(signer.getSigData(callDataNoSig), tokenAddr, st_recip, st_eth_amount, {'from': st_sender})
            elif bals[self.v] < st_eth_amount:
                print('        NOT ENOUGH TOKENS IN VAULT _vault_transfer', tokenAddr, st_sender, st_recip, st_eth_amount, signer)
                with reverts():
                    self.v.transfer(signer.getSigData(callDataNoSig), tokenAddr, st_recip, st_eth_amount, {'from': st_sender})
            elif signer != self.keyIDToCurKeys[AGG]:
                print('        NOT ENOUGH TOKENS IN VAULT _vault_transfer', tokenAddr, st_sender, st_recip, st_eth_amount, signer)
                with reverts(REV_MSG_SIG):
                    self.v.transfer(signer.getSigData(callDataNoSig), tokenAddr, st_recip, st_eth_amount, {'from': st_sender})
            else:
                print('                    _vault_transfer', tokenAddr, st_sender, st_recip, st_eth_amount, signer)
                tx = self.v.transfer(signer.getSigData(callDataNoSig), tokenAddr, st_recip, st_eth_amount, {'from': st_sender})

                bals[self.v] -= st_eth_amount
                bals[st_recip] += st_eth_amount
                self.lastValidateTime = tx.timestamp


        def rule_vault_transfer_eth(self, st_sender, st_recip, st_eth_amount):
            self._vault_transfer(self.ethBals, ETH_ADDR, st_sender, st_recip, st_eth_amount)


        def rule_vault_transfer_tokenA(self, st_sender, st_recip, st_token_amount):
            self._vault_transfer(self.tokenABals, self.tokenA, st_sender, st_recip, st_token_amount)


        def rule_vault_transfer_tokenB(self, st_sender, st_recip, st_token_amount):
            self._vault_transfer(self.tokenBBals, self.tokenB, st_sender, st_recip, st_token_amount)
        

        # Send any combination of eth/tokenA/tokenB out of the vault. Using st_eth_amounts
        # for both eth amounts and token amounts here because its max is within the bounds of
        # both eth and tokens.
        def rule_vault_transferBatch(self, st_sender, st_recips, st_eth_amounts):
            signer = self._get_key_prob(AGG)
            minLen = trimToShortest([st_recips, st_eth_amounts])
            tokens = choices([ETH_ADDR, self.tokenA, self.tokenB], k=minLen)
            callDataNoSig = self.v.transferBatch.encode_input(agg_null_sig(), tokens, st_recips, st_eth_amounts)

            totalEth = 0
            totalTokenA = 0
            totalTokenB = 0
            for tok, am in zip(tokens, st_eth_amounts):
                if tok == ETH_ADDR:
                    totalEth += am
                elif tok == self.tokenA:
                    totalTokenA += am
                elif tok == self.tokenB:
                    totalTokenB += am
                else:
                    assert False, "Unknown asset"
            
            if signer != self.keyIDToCurKeys[AGG]:
                print('        REV_MSG_SIG rule_vault_transferBatch', signer, st_sender, tokens, st_recips, st_eth_amounts)
                with reverts(REV_MSG_SIG):
                    self.v.transferBatch(signer.getSigData(callDataNoSig), tokens, st_recips, st_eth_amounts)
            elif totalEth > self.ethBals[self.v] or totalTokenA > self.tokenABals[self.v] or totalTokenB > self.tokenBBals[self.v]:
                print('        NOT ENOUGH TOKENS IN VAULT rule_vault_transferBatch', signer, st_sender, tokens, st_recips, st_eth_amounts)
                with reverts():
                    self.v.transferBatch(signer.getSigData(callDataNoSig), tokens, st_recips, st_eth_amounts)
            else:
                print('                    rule_vault_transferBatch', signer, st_sender, tokens, st_recips, st_eth_amounts)
                tx = self.v.transferBatch(signer.getSigData(callDataNoSig), tokens, st_recips, st_eth_amounts)

                self.lastValidateTime = tx.timestamp
                for i in range(len(st_recips)):
                    if tokens[i] == ETH_ADDR:
                        self.ethBals[st_recips[i]] += st_eth_amounts[i]
                        self.ethBals[self.v] -= st_eth_amounts[i]
                    elif tokens[i] == self.tokenA:
                        self.tokenABals[st_recips[i]] += st_eth_amounts[i]
                        self.tokenABals[self.v] -= st_eth_amounts[i]
                    elif tokens[i] == self.tokenB:
                        self.tokenBBals[st_recips[i]] += st_eth_amounts[i]
                        self.tokenBBals[self.v] -= st_eth_amounts[i]
                    else:
                        assert False, "Panic"


        # Transfers ETH from a user/sender to one of the depositEth create2 addresses
        def rule_transfer_eth_to_depositEth(self, st_sender, st_swapID, st_eth_amount):
            # No point testing reverts of these conditions since it's not what we're trying to test
            if st_swapID != 0 and self.ethBals[st_sender] >= st_eth_amount:
                print('                    rule_transfer_eth_to_depositEth', st_sender, st_swapID, st_eth_amount)
                depositAddr = getCreate2Addr(self.v.address, cleanHexStrPad(st_swapID), DepositEth, "")
                st_sender.transfer(depositAddr, st_eth_amount)

                self.ethBals[st_sender] -= st_eth_amount
                self.ethBals[depositAddr] += st_eth_amount
        

        # Transfers a token from a user/sender to one of the depositEth create2 addresses.
        # This isn't called directly since rule_transfer_tokens_to_depositTokenA etc use it
        # in the same way but with a different tokenAddr
        def _transfer_tokens_to_token_deposit(self, bals, token, st_sender, st_swapID, st_token_amount):
            # No point testing reverts of these conditions since it's not what we're trying to test
            if st_swapID != 0 and bals[st_sender] >= st_token_amount:
                print('                    _transfer_tokens_to_token_deposit', token, st_sender, st_swapID, st_token_amount)
                depositAddr = getCreate2Addr(self.v.address, cleanHexStrPad(st_swapID), DepositToken, cleanHexStrPad(token.address))
                token.transfer(depositAddr, st_token_amount, {'from': st_sender})

                bals[st_sender] -= st_token_amount
                bals[depositAddr] += st_token_amount
            
        
        # Deposits tokenA from a user to a tokenA create2
        def rule_transfer_tokens_to_depositTokenA(self, st_sender, st_swapID, st_token_amount):
            self._transfer_tokens_to_token_deposit(self.tokenABals, self.tokenA, st_sender, st_swapID, st_token_amount)
            
        
        # Deposits tokenB from a user to a tokenB create2
        def rule_transfer_tokens_to_depositTokenB(self, st_sender, st_swapID, st_token_amount):
            self._transfer_tokens_to_token_deposit(self.tokenBBals, self.tokenB, st_sender, st_swapID, st_token_amount)
        

        # Fetch the ETH deposit of a random create2
        def rule_fetchDepositEth(self, st_sender, st_swapID):
            callDataNoSig = self.v.fetchDepositEth.encode_input(agg_null_sig(), st_swapID)
            signer = self._get_key_prob(AGG)
            
            if st_swapID == 0:
                print('        REV_MSG_NZ_UINT rule_fetchDepositEth', st_sender, st_swapID, signer)
                with reverts(REV_MSG_NZ_UINT):
                    self.v.fetchDepositEth(signer.getSigData(callDataNoSig), st_swapID)
            elif signer != self.keyIDToCurKeys[AGG]:
                print('        REV_MSG_SIG rule_fetchDepositEth', st_sender, st_swapID, signer)
                with reverts(REV_MSG_SIG):
                    self.v.fetchDepositEth(signer.getSigData(callDataNoSig), st_swapID)
            else:
                print('                    rule_fetchDepositEth', st_sender, st_swapID, signer)
                depositAddr = getCreate2Addr(self.v.address, cleanHexStrPad(st_swapID), DepositEth, "")
                depositBal = self.ethBals[depositAddr]
                tx = self.v.fetchDepositEth(signer.getSigData(callDataNoSig), st_swapID)
                
                self.ethBals[depositAddr] -= depositBal
                self.ethBals[self.v] += depositBal
                self.lastValidateTime = tx.timestamp
        

        def rule_fetchDepositEthBatch(self, st_sender, st_swapIDs):
            addrs = [getCreate2Addr(self.v.address, cleanHexStrPad(swapID), DepositEth, "") for swapID in st_swapIDs]
            total = sum([web3.eth.get_balance(addr) for addr in addrs])
            signer = self._get_key_prob(AGG)
            callDataNoSig = self.v.fetchDepositEthBatch.encode_input(agg_null_sig(), st_swapIDs)

            if signer != self.keyIDToCurKeys[AGG]:
                print('        REV_MSG_SIG rule_fetchDepositEthBatch', st_sender, st_swapIDs, signer)
                with reverts(REV_MSG_SIG):
                    self.v.fetchDepositEthBatch(signer.getSigData(callDataNoSig), st_swapIDs)
            else:
                print('                    rule_fetchDepositEthBatch', st_sender, st_swapIDs, signer)
                tx = self.v.fetchDepositEthBatch(signer.getSigData(callDataNoSig), st_swapIDs)

                for addr in addrs:
                    self.ethBals[addr] = 0
                self.ethBals[self.v] += total
                self.lastValidateTime = tx.timestamp
        

        # Fetch the token deposit of a random create2
        def _fetchDepositToken(self, bals, token, st_sender, st_swapID):
            callDataNoSig = self.v.fetchDepositToken.encode_input(agg_null_sig(), st_swapID, token)
            signer = self._get_key_prob(AGG)

            if st_swapID == 0:
                print('        REV_MSG_NZ_UINT _fetchDepositToken', st_sender, st_swapID, signer)
                with reverts(REV_MSG_NZ_UINT):
                    self.v.fetchDepositToken(signer.getSigData(callDataNoSig), st_swapID, token)
            elif signer != self.keyIDToCurKeys[AGG]:
                print('        REV_MSG_SIG _fetchDepositToken', st_sender, st_swapID, signer)
                with reverts(REV_MSG_SIG):
                    self.v.fetchDepositToken(signer.getSigData(callDataNoSig), st_swapID, token)
            else:
                print('                    _fetchDepositToken', token, st_sender, st_swapID, signer)
                depositAddr = getCreate2Addr(self.v.address, cleanHexStrPad(st_swapID), DepositToken, cleanHexStrPad(token.address))
                depositBal = bals[depositAddr]
                tx = self.v.fetchDepositToken(signer.getSigData(callDataNoSig), st_swapID, token)
                
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
            minLen = trimToShortest([st_swapIDs, st_tokens])
            signer = self._get_key_prob(AGG)
            callDataNoSig = self.v.fetchDepositTokenBatch.encode_input(agg_null_sig(), st_swapIDs, st_tokens)
            
            if signer != self.keyIDToCurKeys[AGG]:
                print('        REV_MSG_SIG rule_fetchDepositTokenBatch', st_sender, st_swapIDs, st_tokens, signer)
                with reverts(REV_MSG_SIG):
                    self.v.fetchDepositTokenBatch(signer.getSigData(callDataNoSig), st_swapIDs, st_tokens)
            else:
                for swapID, token in zip(st_swapIDs, st_tokens):
                    addr = getCreate2Addr(self.v.address, cleanHexStrPad(swapID), DepositToken, cleanHexStrPad(token.address))
                    if token == self.tokenA:
                        self.tokenABals[self.v] += self.tokenABals[addr]
                        self.tokenABals[addr] = 0
                    elif token == self.tokenB:
                        self.tokenBBals[self.v] += self.tokenBBals[addr]
                        self.tokenBBals[addr] = 0
                    else:
                        assert False, "Panicc"

                print('                    rule_fetchDepositTokenBatch', st_sender, st_swapIDs, st_tokens, signer)
                tx = self.v.fetchDepositTokenBatch(signer.getSigData(callDataNoSig), st_swapIDs, st_tokens)

                self.lastValidateTime = tx.timestamp
        

        # KeyManager

        # Get the key that is probably what we want, but also has a low chance of choosing
        # the 'wrong' key which will cause a revert and tests the full range. Maximises useful
        # results whilst still testing the full range.
        def _get_key_prob(self, keyID):
            samples = ([self.keyIDToCurKeys[keyID]] * 100) + self.allKeys
            return choice(samples)


        # Checks if isValidSig returns the correct value when called with a random sender,
        # signing key, random keyID that the signing key is supposed to be, and random msgData
        def rule_isValidSig(self, st_sender, st_sig_key_idx, st_keyID_num, st_msg_data):
            sigData = self.allKeys[st_sig_key_idx].getSigData(st_msg_data.hex())

            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[NUM_TO_KEYID[st_keyID_num]]:
                print('                    rule_isValidSig', st_sender, st_sig_key_idx, st_keyID_num, st_msg_data)
                tx = self.km.isValidSig(sigData, cleanHexStr(sigData[0]), st_keyID_num, {'from': st_sender})
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print('        REV_MSG_SIG rule_isValidSig', st_sender, st_sig_key_idx, st_keyID_num, st_msg_data)
                    self.km.isValidSig(sigData, cleanHexStr(sigData[0]), st_keyID_num, {'from': st_sender})

        
        # Replace a key with a random key - either setAggKeyWithAggKey or setGovKeyWithGovKey
        def _set_same_key(self, st_sender, fcn, keyID, st_new_key_idx):
            callDataNoSig = fcn.encode_input(agg_null_sig(), self.allKeys[st_new_key_idx].getPubData())
            signer = self._get_key_prob(keyID)

            if signer == self.keyIDToCurKeys[keyID]:
                print(f'                    {fcn}', st_sender, keyID, signer, st_new_key_idx)
                tx = fcn(signer.getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})

                self.keyIDToCurKeys[keyID] = self.allKeys[st_new_key_idx]
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print(f'        REV_MSG_SIG {fcn}', st_sender, keyID, signer, st_new_key_idx)
                    fcn(signer.getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})


        # Call setAggKeyWithAggKey with a random new key, signing key, and sender
        def rule_setAggKeyWithAggKey(self, st_sender, st_new_key_idx):
            self._set_same_key(st_sender, self.km.setAggKeyWithAggKey, AGG, st_new_key_idx)


        # Call setAggKeyWithAggKey with a random new key, signing key, and sender
        def rule_setGovKeyWithGovKey(self, st_sender, st_new_key_idx):
            self._set_same_key(st_sender, self.km.setGovKeyWithGovKey, GOV, st_new_key_idx)
        

        # Sleep for a random time so that setAggKeyWithGovKey can be called without reverting
        def rule_sleep(self, st_sleep_time):
            print('                    rule_sleep', st_sleep_time)
            chain.sleep(st_sleep_time)
        

        # Useful results are being impeded by most attempts at setAggKeyWithGovKey not having enough
        # delay - having 2 sleep methods makes it more common aswell as this which is enough of a delay
        # in itself, since Hypothesis usually picks small values as part of shrinking
        def rule_sleep_2_days(self):
            print('                    rule_sleep_2_days')
            chain.sleep(2 * DAY)


        # Call setAggKeyWithGovKey with a random new key, signing key, and sender
        def rule_setAggKeyWithGovKey(self, st_sender, st_new_key_idx):
            callDataNoSig = self.km.setAggKeyWithGovKey.encode_input(gov_null_sig(), self.allKeys[st_new_key_idx].getPubData())
            signer = self._get_key_prob(GOV)

            if chain.time() - self.lastValidateTime < AGG_KEY_TIMEOUT:
                print('        REV_MSG_DELAY rule_setAggKeyWithGovKey', st_sender, signer, st_new_key_idx)
                with reverts(REV_MSG_DELAY):
                    self.km.setAggKeyWithGovKey(signer.getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})
            elif signer != self.keyIDToCurKeys[GOV]:
                print('        REV_MSG_SIG rule_setAggKeyWithGovKey', st_sender, signer, st_new_key_idx)
                with reverts(REV_MSG_SIG):
                    self.km.setAggKeyWithGovKey(signer.getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})
            else:
                print('                    rule_setAggKeyWithGovKey', st_sender, signer, st_new_key_idx)
                tx = self.km.setAggKeyWithGovKey(signer.getSigData(callDataNoSig), self.allKeys[st_new_key_idx].getPubData(), {'from': st_sender})

                self.keyIDToCurKeys[AGG] = self.allKeys[st_new_key_idx]
                self.lastValidateTime = tx.timestamp
        

        # StakeManager


        # Stakes a random amount from a random staker to a random nodeID
        def rule_stake(self, st_staker, st_nodeID, st_stake, st_returnAddr):
            if st_nodeID == 0:
                print('        rule_stake NODEID', st_staker, st_nodeID, st_stake/E_18)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.stake(st_nodeID, st_stake, st_returnAddr, {'from': st_staker})
            elif st_stake < self.minStake:
            # st_stake = MAX_TEST_STAKE - st_stake
            # if st_stake < self.minStake:
                print('        rule_stake MIN_STAKE', st_staker, st_nodeID, st_stake/E_18)
                with reverts(REV_MSG_MIN_STAKE):
                    self.sm.stake(st_nodeID, st_stake, st_returnAddr, {'from': st_staker})
            elif st_stake > self.flipBals[st_staker]:
                print('        rule_stake REV_MSG_ERC777_EXCEED_BAL', st_staker, st_nodeID, st_stake/E_18)
                with reverts(REV_MSG_ERC777_EXCEED_BAL):
                    self.sm.stake(st_nodeID, st_stake, st_returnAddr, {'from': st_staker})
            else:
                print('                    rule_stake ', st_staker, st_nodeID, st_stake/E_18)
                tx = self.sm.stake(st_nodeID, st_stake, st_returnAddr, {'from': st_staker})

                self.flipBals[st_staker] -= st_stake
                self.flipBals[self.sm] += st_stake
                self.totalStake += st_stake
            

        # Claims a random amount from a random nodeID to a random recipient
        def rule_registerClaim(self, st_nodeID, st_staker, st_stake, st_sender, st_expiry_time_diff):
            args = (st_nodeID, st_stake, st_staker, chain.time() + st_expiry_time_diff)
            callDataNoSig = self.sm.registerClaim.encode_input(agg_null_sig(), *args)
            signer = self._get_key_prob(AGG)

            if st_nodeID == 0:
                print('        NODEID rule_registerClaim', *args)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.registerClaim(signer.getSigData(callDataNoSig), *args, {'from': st_sender})
            elif st_stake == 0:
                print('        AMOUNT rule_registerClaim', *args)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.registerClaim(signer.getSigData(callDataNoSig), *args, {'from': st_sender})
            elif signer != self.keyIDToCurKeys[AGG]:
                print('        REV_MSG_SIG rule_registerClaim', *args)
                with reverts(REV_MSG_SIG):
                    self.sm.registerClaim(signer.getSigData(callDataNoSig), *args, {'from': st_sender})
            elif chain.time() <= self.pendingClaims[st_nodeID][3]:
                print('        REV_MSG_CLAIM_EXISTS rule_registerClaim', *args)
                with reverts(REV_MSG_CLAIM_EXISTS):
                    self.sm.registerClaim(signer.getSigData(callDataNoSig), *args, {'from': st_sender})
            elif st_expiry_time_diff <= CLAIM_DELAY:
                print('        REV_MSG_EXPIRY_TOO_SOON rule_registerClaim', *args)
                with reverts(REV_MSG_EXPIRY_TOO_SOON):
                    self.sm.registerClaim(signer.getSigData(callDataNoSig), *args, {'from': st_sender})
            else:
                print('                    rule_registerClaim ', *args)
                tx = self.sm.registerClaim(signer.getSigData(callDataNoSig), *args, {'from': st_sender})

                self.pendingClaims[st_nodeID] = (st_stake, st_staker, tx.timestamp + CLAIM_DELAY, args[3])
                self.lastValidateTime = tx.timestamp
        

        # Executes a random claim
        def rule_executeClaim(self, st_nodeID, st_sender):
            inflation = getInflation(self.lastMintBlockNum, web3.eth.block_number + 1, self.emissionPerBlock)
            claim = self.pendingClaims[st_nodeID]

            if not claim[2] <= chain.time() <= claim[3]:
                print('        REV_MSG_NOT_ON_TIME rule_executeClaim', st_nodeID)
                with reverts(REV_MSG_NOT_ON_TIME):
                    self.sm.executeClaim(st_nodeID, {'from': st_sender})
            elif self.flipBals[self.sm] + inflation < claim[0]:
                print('        REV_MSG_ERC777_EXCEED_BAL rule_executeClaim', st_nodeID)
                with reverts(REV_MSG_ERC777_EXCEED_BAL):
                    self.sm.executeClaim(st_nodeID, {'from': st_sender})
            else:
                print('                    rule_executeClaim', st_nodeID)
                tx = self.sm.executeClaim(st_nodeID, {'from': st_sender})

                self.flipBals[claim[1]] += claim[0]
                self.flipBals[self.sm] -= (claim[0] - inflation)
                self.totalStake -= (claim[0] - inflation)
                self.lastMintBlockNum = tx.block_number
                self.pendingClaims[st_nodeID] = NULL_CLAIM
        
        
        # Sets the emission rate as a random value, signs with a random (probability-weighted) sig,
        # and sends the tx from a random address
        def rule_setEmissionPerBlock(self, st_emission, st_sender):
            callDataNoSig = self.sm.setEmissionPerBlock.encode_input(gov_null_sig(), st_emission)
            signer = self._get_key_prob(GOV)

            if st_emission == 0:
                print('        rule_setEmissionPerBlock REV_MSG_NZ_UINT', st_emission, signer, st_sender)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.setEmissionPerBlock(signer.getSigData(callDataNoSig), st_emission, {'from': st_sender})
            elif signer != self.keyIDToCurKeys[GOV]:
                print('        rule_setEmissionPerBlock REV_MSG_SIG', st_emission, signer, st_sender)
                with reverts(REV_MSG_SIG):
                    self.sm.setEmissionPerBlock(signer.getSigData(callDataNoSig), st_emission, {'from': st_sender})
            else:
                print('                    rule_setEmissionPerBlock', st_emission, signer, st_sender)
                tx = self.sm.setEmissionPerBlock(signer.getSigData(callDataNoSig), st_emission, {'from': st_sender})

                inflation = getInflation(self.lastMintBlockNum, web3.eth.block_number, self.emissionPerBlock)
                self.flipBals[self.sm] += inflation
                self.totalStake += inflation
                self.lastMintBlockNum = tx.block_number
                self.emissionPerBlock = st_emission
                self.lastValidateTime = tx.timestamp


        # Sets the minimum stake as a random value, signs with a random (probability-weighted) sig,
        # and sends the tx from a random address
        def rule_setMinStake(self, st_minStake, st_sender):
            callDataNoSig = self.sm.setMinStake.encode_input(gov_null_sig(), st_minStake)
            signer = self._get_key_prob(GOV)

            if st_minStake == 0:
                print('        rule_setMinstake REV_MSG_NZ_UINT', st_minStake, signer, st_sender)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.setMinStake(signer.getSigData(callDataNoSig), st_minStake, {'from': st_sender})
            elif signer != self.keyIDToCurKeys[GOV]:
                print('        rule_setMinstake REV_MSG_SIG', st_minStake, signer, st_sender)
                with reverts(REV_MSG_SIG):
                    self.sm.setMinStake(signer.getSigData(callDataNoSig), st_minStake, {'from': st_sender})
            else:
                print('                    rule_setMinstake', st_minStake, signer, st_sender)
                tx = self.sm.setMinStake(signer.getSigData(callDataNoSig), st_minStake, {'from': st_sender})

                self.minStake = st_minStake
                self.lastValidateTime = tx.timestamp


        # Check all the balances of every address are as they should be after every tx
        def invariant_bals(self):
            self.numTxsTested += 1
            for addr in self.allAddrs:
                assert web3.eth.get_balance(str(addr)) == self.ethBals[addr]
                assert self.tokenA.balanceOf(addr) == self.tokenABals[addr]
                assert self.tokenB.balanceOf(addr) == self.tokenBBals[addr]
        

        # Variable(s) that shouldn't change since there's no intentional way to
        def invariant_nonchangeable(self):
            assert self.v.getKeyManager() == self.km.address
            assert self.sm.getKeyManager() == self.km.address
            assert self.sm.getFLIPAddress() == self.f.address
        

        # Check the keys are correct after every tx
        def invariant_keys(self):
            assert self.km.getAggregateKey() == self.keyIDToCurKeys[AGG].getPubDataWith0x()
            assert self.km.getGovernanceKey() == self.keyIDToCurKeys[GOV].getPubDataWith0x()
        

        # Check the intentionally changeable variables after every tx
        def invariant_state_vars(self):
            assert self.sm.getLastMintBlockNum() == self.lastMintBlockNum
            assert self.sm.getEmissionPerBlock() == self.emissionPerBlock
            assert self.sm.getMinimumStake() == self.minStake
            assert self.km.getLastValidateTime() == self.lastValidateTime
            for nodeID, claim in self.pendingClaims.items():
                assert self.sm.getPendingClaim(nodeID) == claim


        def invariant_inflation_calcs(self):
            # Test in present and future
            assert self.sm.getInflationInFuture(0) == getInflation(self.lastMintBlockNum, web3.eth.block_number, self.emissionPerBlock)
            assert self.sm.getInflationInFuture(100) == getInflation(self.lastMintBlockNum, web3.eth.block_number+100, self.emissionPerBlock)
            assert self.sm.getTotalStakeInFuture(0) == self.totalStake + getInflation(self.lastMintBlockNum, web3.eth.block_number, self.emissionPerBlock)
            assert self.sm.getTotalStakeInFuture(100) == self.totalStake + getInflation(self.lastMintBlockNum, web3.eth.block_number+100, self.emissionPerBlock)
        
        
        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f'Total rules executed = {self.numTxsTested-1}')

    
    state_machine(StateMachine, a, cfDeploy, DepositEth, DepositToken, Token, settings=settings)