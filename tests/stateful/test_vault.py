from consts import *
from brownie import reverts, chain, web3
from brownie.test import strategy


def test_vault(BaseStateMachine, state_machine, a, cfDeploy, DepositEth, DepositToken, Token):
    MAX_SWAPID = 5
    MAX_NUM_SENDERS = 5
    INIT_ETH = 100 * E_18
    MAX_ETH_SEND = E_18
    MAX_TOKEN_SEND = 10**23
    INIT_TOKEN_AMNT = MAX_TOKEN_SEND * 100
    
    class StateMachine(BaseStateMachine):

        def __init__(cls, a, cfDeploy, DepositEth, DepositToken, Token):
            # cls.aaa = {addr: addr for addr, addr in enumerate(a)}
            super().__init__(cls, a, cfDeploy)
            cls.tokenA = a[0].deploy(Token, "ShitcoinA", "SCA", INIT_TOKEN_SUPPLY)
            cls.tokenB = a[0].deploy(Token, "ShitcoinB", "SCB", INIT_TOKEN_SUPPLY)

            for token in [cls.tokenA, cls.tokenB]:
                for recip in a[1:]:
                    token.transfer(recip, INIT_TOKEN_AMNT)
            
            cls.create2EthAddrs = [getCreate2Addr(cls.v.address, cleanHexStrPad(swapID), DepositEth, "") for swapID in range(MAX_SWAPID+1)]
            cls.create2TokenAAddrs = [getCreate2Addr(cls.v.address, cleanHexStrPad(swapID), DepositToken, cleanHexStrPad(cls.tokenA.address)) for swapID in range(MAX_SWAPID+1)]
            cls.create2TokenBAddrs = [getCreate2Addr(cls.v.address, cleanHexStrPad(swapID), DepositToken, cleanHexStrPad(cls.tokenB.address)) for swapID in range(MAX_SWAPID+1)]
            cls.allAddrs = [*[addr.address for addr in a[0:MAX_NUM_SENDERS]], *cls.create2EthAddrs, *cls.create2TokenAAddrs, *cls.create2TokenBAddrs, cls.v.address]


        def setup(self):
            self.ethBals = {addr: INIT_ETH if addr in a else 0 for addr in self.allAddrs}
            self.tokenABals = {addr: INIT_TOKEN_AMNT if addr in a else 0 for addr in self.allAddrs}
            self.tokenBBals = {addr: INIT_TOKEN_AMNT if addr in a else 0 for addr in self.allAddrs}


        st_eth_amount = strategy("uint", max_value=MAX_ETH_SEND)
        st_token_amount = strategy("uint", max_value=MAX_TOKEN_SEND)
        st_swapID = strategy("uint", min_value=1, max_value=MAX_SWAPID)
        # Only want the 1st 5 addresses so that the chances of multiple
        # txs occurring from the same address is greatly increased while still
        # ensuring diversity in senders
        st_sender = strategy("address", length=MAX_NUM_SENDERS)
        st_recip = strategy("address", length=MAX_NUM_SENDERS)
        # st_recip = strategy("address")


        def _vault_transfer(self, bals, tokenAddr, st_sender, st_recip, st_eth_amount):
            callDataNoSig = self.v.transfer.encode_input(NULL_SIG_DATA, tokenAddr, st_recip, st_eth_amount)
            
            if st_eth_amount > 0:
                if bals[self.v.address] >= st_eth_amount:
                    self.v.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), tokenAddr, st_recip, st_eth_amount, {'from': st_sender})

                    bals[self.v.address] -= st_eth_amount
                    bals[st_recip] += st_eth_amount
                else:
                    with reverts():
                        self.v.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), tokenAddr, st_recip, st_eth_amount)
            else:
                with reverts(REV_MSG_NZ_UINT):
                    self.v.transfer(AGG_SIGNER_1.getSigData(callDataNoSig), tokenAddr, st_recip, st_eth_amount)


        def rule_vault_transfer_eth(self, st_sender, st_recip, st_eth_amount):
            self._vault_transfer(self.ethBals, ETH_ADDR, st_sender, st_recip, st_eth_amount)



        def rule_vault_transfer_tokenA(self, st_sender, st_recip, st_token_amount):
            self._vault_transfer(self.tokenABals, self.tokenA, st_sender, st_recip, st_token_amount)


        def rule_vault_transfer_tokenB(self, st_sender, st_recip, st_token_amount):
            self._vault_transfer(self.tokenBBals, self.tokenB, st_sender, st_recip, st_token_amount)
        

        def rule_transfer_eth_to_depositEth(self, st_sender, st_swapID, st_eth_amount):
            if st_swapID != 0 and self.ethBals[st_sender] >= st_eth_amount:
                depositAddr = getCreate2Addr(self.v.address, cleanHexStrPad(st_swapID), DepositEth, "")
                st_sender.transfer(depositAddr, st_eth_amount)

                self.ethBals[st_sender] -= st_eth_amount
                self.ethBals[depositAddr] += st_eth_amount
        

        def _transfer_tokens_to_token_deposit(self, bals, token, st_sender, st_swapID, st_token_amount):
            if st_swapID != 0 and bals[st_sender] >= st_token_amount:
                depositAddr = getCreate2Addr(self.v.address, cleanHexStrPad(st_swapID), DepositToken, cleanHexStrPad(token.address))
                token.transfer(depositAddr, st_token_amount, {'from': st_sender})

                bals[st_sender] -= st_token_amount
                bals[depositAddr] += st_token_amount
            
        
        def rule_transfer_tokens_to_depositTokenA(self, st_sender, st_swapID, st_token_amount):
            self._transfer_tokens_to_token_deposit(self.tokenABals, self.tokenA, st_sender, st_swapID, st_token_amount)
            
        
        def rule_transfer_tokens_to_depositTokenB(self, st_sender, st_swapID, st_token_amount):
            self._transfer_tokens_to_token_deposit(self.tokenBBals, self.tokenB, st_sender, st_swapID, st_token_amount)
        

        def rule_fetchDepositEth(self, st_sender, st_swapID):
            if st_swapID != 0:
                depositAddr = getCreate2Addr(self.v.address, cleanHexStrPad(st_swapID), DepositEth, "")
                depositBal = self.ethBals[depositAddr]
                callDataNoSig = self.v.fetchDepositEth.encode_input(NULL_SIG_DATA, st_swapID)
                self.v.fetchDepositEth(AGG_SIGNER_1.getSigData(callDataNoSig), st_swapID)
                
                self.ethBals[depositAddr] -= depositBal
                self.ethBals[self.v.address] += depositBal
        

        def _fetchDepositToken(self, bals, token, st_sender, st_swapID):
            if st_swapID != 0:
                depositAddr = getCreate2Addr(self.v.address, cleanHexStrPad(st_swapID), DepositToken, cleanHexStrPad(token.address))
                depositBal = bals[depositAddr]
                callDataNoSig = self.v.fetchDepositToken.encode_input(NULL_SIG_DATA, st_swapID, token)
                self.v.fetchDepositToken(AGG_SIGNER_1.getSigData(callDataNoSig), st_swapID, token)
                
                bals[depositAddr] -= depositBal
                bals[self.v.address] += depositBal
        

        def rule_fetchDepositToken_tokenA(self, st_sender, st_swapID):
            self._fetchDepositToken(self.tokenABals, self.tokenA, st_sender, st_swapID)
        

        def rule_fetchDepositToken_tokenB(self, st_sender, st_swapID):
            self._fetchDepositToken(self.tokenBBals, self.tokenB, st_sender, st_swapID)

                

        def invariant_bals(self):
            for addr in self.allAddrs:
                assert web3.eth.getBalance(addr) == self.ethBals[addr]
                assert self.tokenA.balanceOf(addr) == self.tokenABals[addr]
                assert self.tokenB.balanceOf(addr) == self.tokenBBals[addr]
        

    
    settings = {"stateful_step_count": 10, "max_examples": 10}
    state_machine(StateMachine, a, cfDeploy, DepositEth, DepositToken, Token, settings=settings)