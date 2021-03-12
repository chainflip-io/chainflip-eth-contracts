from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy
from utils import *
from hypothesis import strategies as hypStrat
import random


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

        There's a NUM_STAKERS number of stakers that randomly `stake` and are randomly 
        the recipients of `claim`. The parameters used are so that they're small enough 
        to increase the likelihood of the same address being used in multiple 
        interactions (e.g. 2  x stakes then a claim etc) and large enough to ensure 
        there's variety in them.

        The parameters used are so that they're small enough to increase the likelihood of the same
        address being used in multiple interactions and large enough to ensure there's variety in them
        """

        def __init__(cls, a, cfDeploy, DepositEth, DepositToken, Token):
            super().__init__(cls, a, cfDeploy)

            cls.tokenA = a[0].deploy(Token, "NotAPonziA", "NAPA", INIT_TOKEN_SUPPLY)
            cls.tokenB = a[0].deploy(Token, "NotAPonziB", "NAPB", INIT_TOKEN_SUPPLY)

            for token in [cls.tokenA, cls.tokenB]:
                for recip in a[1:]:
                    token.transfer(recip, INIT_TOKEN_AMNT)
            
            cls.create2EthAddrs = [getCreate2Addr(cls.v.address, cleanHexStrPad(swapID), DepositEth, "") for swapID in range(MAX_SWAPID+1)]
            cls.create2TokenAAddrs = [getCreate2Addr(cls.v.address, cleanHexStrPad(swapID), DepositToken, cleanHexStrPad(cls.tokenA.address)) for swapID in range(MAX_SWAPID+1)]
            cls.create2TokenBAddrs = [getCreate2Addr(cls.v.address, cleanHexStrPad(swapID), DepositToken, cleanHexStrPad(cls.tokenB.address)) for swapID in range(MAX_SWAPID+1)]

            cls.stakers = a[:MAX_NUM_SENDERS]

            for staker in cls.stakers:
                cls.f.transfer(staker, INIT_STAKE, {'from': a[0]})
                cls.f.approve(cls.sm, INIT_STAKE, {'from': staker})
            # Send excess from the deployer to the zero address so that all stakers start
            # with the same balance to make the accounting simpler
            cls.f.transfer("0x0000000000000000000000000000000000000001", cls.f.balanceOf(a[0]) - INIT_STAKE, {'from': a[0]})


        def setup(self):
            self.allAddrs = self.stakers + [self.sm]
            self.allAddrs = [*[addr.address for addr in self.stakers], *self.create2EthAddrs, 
                *self.create2TokenAAddrs, *self.create2TokenBAddrs, self.v, self.km, self.sm]
            
            callDataNoSig = self.sm.setMinStake.encode_input(NULL_SIG_DATA, INIT_MIN_STAKE)
            tx = self.sm.setMinStake(GOV_SIGNER_1.getSigData(callDataNoSig), INIT_MIN_STAKE)

            # Vault
            self.ethBals = {addr: INIT_ETH_BAL if addr in a else 0 for addr in self.allAddrs}
            self.tokenABals = {addr: INIT_TOKEN_AMNT if addr in a else 0 for addr in self.allAddrs}
            self.tokenBBals = {addr: INIT_TOKEN_AMNT if addr in a else 0 for addr in self.allAddrs}
            
            # KeyManager
            self.lastValidateTime = tx.timestamp
            self.keyIDToCurKeys = {AGG: AGG_SIGNER_1, GOV: GOV_SIGNER_1}
            self.allKeys = [*self.keyIDToCurKeys.values()] + ([Signer.gen_signer()] * (TOTAL_KEYS - 2))

            # StakeManager
            self.lastMintBlockNum = self.sm.tx.block_number
            self.emissionPerBlock = EMISSION_PER_BLOCK
            self.totalStake = 0
            self.minStake = INIT_MIN_STAKE
            self.flipBals = {addr: INIT_STAKE if addr in self.stakers else 0 for addr in self.allAddrs}
            self.numTxsTested = 0


        # Variables that will be a random value with each fcn/rule called

        # Vault

        st_eth_amount = strategy("uint", max_value=MAX_ETH_SEND)
        st_token_amount = strategy("uint", max_value=MAX_TOKEN_SEND)
        st_swapID = strategy("uint", min_value=1, max_value=MAX_SWAPID)
        # Only want the 1st 5 addresses so that the chances of multiple
        # txs occurring from the same address is greatly increased while still
        # ensuring diversity in senders
        st_sender = strategy("address", length=MAX_NUM_SENDERS)
        st_recip = strategy("address", length=MAX_NUM_SENDERS)

        # KeyManager

        st_sig_key_idx = strategy("uint", max_value=TOTAL_KEYS-1)
        st_new_key_idx = strategy("uint", max_value=TOTAL_KEYS-1)
        st_keyID_num = strategy("uint", max_value=len(KEYID_TO_NUM)-1)
        st_msg_data = strategy("bytes")
        st_sleep_time = strategy("uint", max_value=7 * DAY, exclude=0)

        # StakeManager

        st_staker = strategy("address", length=MAX_NUM_SENDERS)
        st_nodeID = strategy("uint")
        st_stake = strategy("uint", max_value=MAX_TEST_STAKE)
        # This would be 10x the initial supply in 1 year, so is a reasonable max without
        # uint overflowing
        st_emission = strategy("uint", max_value=370 * E_18)
        # In reality this high amount isn't really realistic, but for the sake of testing
        st_minStake = strategy("uint", max_value=int(INIT_STAKE/2))
        # So there's a 1% chance of a bad sig to maximise useful txs
        st_signer_agg = hypStrat.sampled_from(([AGG_SIGNER_1] * 99) + [GOV_SIGNER_1])


        # Vault


        # Transfers ETH or tokens out the vault. Want this to be called by rule_vault_transfer_eth
        # etc individually and not directly since they're all the same just with a different tokenAddr
        # input
        def _vault_transfer(self, bals, tokenAddr, st_sender, st_recip, st_eth_amount):
            callDataNoSig = self.v.transfer.encode_input(NULL_SIG_DATA, tokenAddr, st_recip, st_eth_amount)
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
            callDataNoSig = self.v.fetchDepositEth.encode_input(NULL_SIG_DATA, st_swapID)
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
        

        # Fetch the token deposit of a random create2
        def _fetchDepositToken(self, bals, token, st_sender, st_swapID):
            callDataNoSig = self.v.fetchDepositToken.encode_input(NULL_SIG_DATA, st_swapID, token)
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
        

        # KeyManager

        # Get the key that is probably what we want, but also has a low chance of choosing
        # the 'wrong' key which will cause a revert and tests the full range. Maximises useful
        # results whilst still testing the full range.
        def _get_key_prob(self, keyID):
            samples = ([self.keyIDToCurKeys[keyID]] * 100) + self.allKeys
            return random.choice(samples)


        # Checks if isValidSig returns the correct value when called with a random sender,
        # signing key, random keyID that the signing key is supposed to be, and random msgData
        def rule_isValidSig(self, st_sender, st_sig_key_idx, st_keyID_num, st_msg_data):
            sigData = self.allKeys[st_sig_key_idx].getSigData(st_msg_data.hex())

            if self.allKeys[st_sig_key_idx] == self.keyIDToCurKeys[NUM_TO_KEYID[st_keyID_num]]:
                print('                    rule_isValidSig', st_sender, st_sig_key_idx, st_keyID_num, st_msg_data)
                tx = self.km.isValidSig(cleanHexStr(sigData[0]), sigData, st_keyID_num, {'from': st_sender})
                self.lastValidateTime = tx.timestamp
            else:
                with reverts(REV_MSG_SIG):
                    print('        REV_MSG_SIG rule_isValidSig', st_sender, st_sig_key_idx, st_keyID_num, st_msg_data)
                    self.km.isValidSig(cleanHexStr(sigData[0]), sigData, st_keyID_num, {'from': st_sender})

        
        # Replace a key with a random key - either setAggKeyWithAggKey or setGovKeyWithGovKey
        def _set_same_key(self, st_sender, fcn, keyID, st_new_key_idx):
            callDataNoSig = fcn.encode_input(NULL_SIG_DATA, self.allKeys[st_new_key_idx].getPubData())
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
            chain.sleep(st_sleep_time)
        

        # Useful results are being impeded by most attempts at setAggKeyWithGovKey not having enough
        # delay - having 2 sleep methods makes it more common aswell as this which is enough of a delay
        # in itself, since Hypothesis usually picks small values as part of shrinking
        def rule_sleep_2_days(self):
            chain.sleep(2 * DAY)


        # Call setAggKeyWithGovKey with a random new key, signing key, and sender
        def rule_setAggKeyWithGovKey(self, st_sender, st_new_key_idx):
            callDataNoSig = self.km.setAggKeyWithGovKey.encode_input(NULL_SIG_DATA, self.allKeys[st_new_key_idx].getPubData())
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
        def rule_stake(self, st_staker, st_nodeID, st_stake):
            if st_nodeID == 0:
                print('        rule_stake NODEID', st_staker, st_nodeID, st_stake/E_18)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.stake(st_nodeID, st_stake, {'from': st_staker})
            elif st_stake < self.minStake:
            # st_stake = MAX_TEST_STAKE - st_stake
            # if st_stake < self.minStake:
                print('        rule_stake MIN_STAKE', st_staker, st_nodeID, st_stake/E_18)
                with reverts(REV_MSG_MIN_STAKE):
                    self.sm.stake(st_nodeID, st_stake, {'from': st_staker})
            elif st_stake > self.flipBals[st_staker]:
                print('        rule_stake REV_MSG_EXCEED_BAL', st_staker, st_nodeID, st_stake/E_18)
                with reverts(REV_MSG_EXCEED_BAL):
                    self.sm.stake(st_nodeID, st_stake, {'from': st_staker})
            else:
                print('                    rule_stake ', st_staker, st_nodeID, st_stake/E_18)
                tx = self.sm.stake(st_nodeID, st_stake, {'from': st_staker})

                self.flipBals[st_staker] -= st_stake
                self.flipBals[self.sm] += st_stake
                self.totalStake += st_stake
            

        # Claims a random amount from a random nodeID to a random recipient
        def rule_claim(self, st_nodeID, st_staker, st_stake, st_sender):
            callDataNoSig = self.sm.claim.encode_input(NULL_SIG_DATA, st_nodeID, st_staker, st_stake)
            inflation = getInflation(self.lastMintBlockNum, web3.eth.blockNumber + 1, self.emissionPerBlock)
            signer = self._get_key_prob(AGG)

            if st_nodeID == 0:
                print('        rule_claim NODEID', st_staker, st_nodeID, st_stake/E_18)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.claim(signer.getSigData(callDataNoSig), st_nodeID, st_staker, st_stake, {'from': st_sender})
            elif st_stake == 0:
                print('        rule_claim AMOUNT', st_staker, st_nodeID, st_stake/E_18)
                with reverts(REV_MSG_NZ_UINT):
                    self.sm.claim(signer.getSigData(callDataNoSig), st_nodeID, st_staker, st_stake, {'from': st_sender})
            elif signer != self.keyIDToCurKeys[AGG]:
                print('        rule_claim REV_MSG_SIG', st_staker, st_nodeID, st_stake/E_18)
                with reverts(REV_MSG_SIG):
                    self.sm.claim(signer.getSigData(callDataNoSig), st_nodeID, st_staker, st_stake, {'from': st_sender})
            elif st_stake > self.flipBals[self.sm] + inflation:
                print('        rule_claim REV_MSG_EXCEED_BAL', st_staker, st_nodeID, st_stake/E_18)
                with reverts(REV_MSG_EXCEED_BAL):
                    self.sm.claim(signer.getSigData(callDataNoSig), st_nodeID, st_staker, st_stake, {'from': st_sender})
            else:
                print('                    rule_claim ', st_staker, st_nodeID, st_stake/E_18)
                tx = self.sm.claim(signer.getSigData(callDataNoSig), st_nodeID, st_staker, st_stake, {'from': st_sender})

                self.flipBals[st_staker] += st_stake
                self.flipBals[self.sm] -= (st_stake - inflation)
                self.totalStake -= (st_stake - inflation)
                self.lastMintBlockNum = tx.block_number
                self.lastValidateTime = tx.timestamp
        

        # Sets the emission rate as a random value, signs with a random (probability-weighted) sig,
        # and sends the tx from a random address
        def rule_setEmissionPerBlock(self, st_emission, st_sender):
            callDataNoSig = self.sm.setEmissionPerBlock.encode_input(NULL_SIG_DATA, st_emission)
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

                inflation = getInflation(self.lastMintBlockNum, web3.eth.blockNumber, self.emissionPerBlock)
                self.flipBals[self.sm] += inflation
                self.totalStake += inflation
                self.lastMintBlockNum = tx.block_number
                self.emissionPerBlock = st_emission
                self.lastValidateTime = tx.timestamp


        # Sets the minimum stake as a random value, signs with a random (probability-weighted) sig,
        # and sends the tx from a random address
        def rule_setMinStake(self, st_minStake, st_sender):
            callDataNoSig = self.sm.setMinStake.encode_input(NULL_SIG_DATA, st_minStake)
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
                assert web3.eth.getBalance(str(addr)) == self.ethBals[addr]
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


        def invariant_inflation_calcs(self):
            # Test in present and future
            assert self.sm.getInflationInFuture(0) == getInflation(self.lastMintBlockNum, web3.eth.blockNumber, self.emissionPerBlock)
            assert self.sm.getInflationInFuture(100) == getInflation(self.lastMintBlockNum, web3.eth.blockNumber+100, self.emissionPerBlock)
            assert self.sm.getTotalStakeInFuture(0) == self.totalStake + getInflation(self.lastMintBlockNum, web3.eth.blockNumber, self.emissionPerBlock)
            assert self.sm.getTotalStakeInFuture(100) == self.totalStake + getInflation(self.lastMintBlockNum, web3.eth.blockNumber+100, self.emissionPerBlock)
        
        
        # Print how many rules were executed at the end of each run
        def teardown(self):
            print(f'Total rules executed = {self.numTxsTested-1}')

    
    settings = {"stateful_step_count": 500, "max_examples": 50}
    state_machine(StateMachine, a, cfDeploy, DepositEth, DepositToken, Token, settings=settings)