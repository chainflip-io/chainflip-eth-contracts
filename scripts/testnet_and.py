from brownie import chain, accounts, KeyManager, Vault, StakeManager, FLIP, network

### A bit of a hack so we can reuse the chainflip test deployment
#
import sys
from os import path
sys.path.append(path.abspath('tests'))

## Any import statements that are relative to the `tests` dir should go here.

from consts import *

sys.path.pop()
#
###

class Chainflip:
    '''
    A very simple context manager to deploy the chainflip contracts and seed some accounts. Based on 
    deploy_initial_ChainFlip_contracts() in conftest.py.

    Can be used from brownie like this: `brownie run deploy_and stake_alice_and_bob`. 
    '''

    def __init__(self):
        self.deployed = False


        self.keyManager = None
        self.vault = None
        self.stakeManager = None
        self.flip = None

        print(f'!!!!! Network is {network.show_active()} !!!!!')
        if network.show_active() == 'ropsten':
            accounts.from_mnemonic("science slender utility quick whip side lesson tent innocent elephant misery move", count=10)
            self.DEPLOYER = accounts[0]
            self.ALICE = accounts[1]
            self.BOB = accounts[2]
            self.CHARLIE = accounts[3]
            self.DENICE = accounts[4]

            self.keyManager = KeyManager.at("0xAA5dBBa22c7c4c4B2c2FEaCe9552F0075651F4aC")
            self.vault = Vault.at("0xB1514Dc0A818643b613B7CF135ef4F60b84B6364")
            self.stakeManager = StakeManager.at("0x693D79a417bAD0c0d07060e0b11635F438CBcd7A")
            self.flip = FLIP.at(self.stakeManager.getFLIPAddress())
        else:
            self.DEPLOYER = accounts[0]
            self.ALICE = accounts[1]
            self.BOB = accounts[2]
            self.CHARLIE = accounts[3]
            self.DENICE = accounts[4]
            
            self.keyManager = self.DEPLOYER.deploy(KeyManager, AGG_SIGNER_1.getPubData(), GOV_SIGNER_1.getPubData())
            self.vault = self.DEPLOYER.deploy(Vault, self.keyManager)
            self.stakeManager = self.DEPLOYER.deploy(StakeManager, self.keyManager, EMISSION_PER_BLOCK, MIN_STAKE, INIT_SUPPLY)
            self.flip = FLIP.at(self.stakeManager.getFLIPAddress())


    def __enter__(self):
        return self


    def __exit__(self, *args):
        return self


    def deploy(self):
        print(f"\n💾 Deploying chainflip contracts in {path.abspath((path.curdir))}\n")
        
        self.keyManager = self.DEPLOYER.deploy(KeyManager, AGG_SIGNER_1.getPubData(), GOV_SIGNER_1.getPubData())
        self.vault = self.DEPLOYER.deploy(Vault, self.keyManager)
        self.stakeManager = self.DEPLOYER.deploy(StakeManager, self.keyManager, EMISSION_PER_BLOCK, MIN_STAKE, INIT_SUPPLY)
        self.flip = FLIP.at(self.stakeManager.getFLIPAddress())

        print("========================= 😎  Deployed! 😎 ==========================\n")
        print(f"KeyManager deployed by {self.DEPLOYER} to address: {self.keyManager.address}\n")
        print(f"Vault deployed by {self.DEPLOYER} to address: {self.vault.address}\n")
        print(f"StakeManager deployed by {self.DEPLOYER} to address: {self.stakeManager.address}\n")
        print(f"FLIP deployed by {self.DEPLOYER} to address: {self.stakeManager.getFLIPAddress()}\n")
        print("======================================================================")
    
    
    def seed_eth(self, addrs):
        print('seeding eth')
        print(addrs)
        for addr in addrs:
            bal = addr.balance()
            print(bal)
            print(addr != self.DEPLOYER)
            print(bal < int(E_18/2))
            if addr != self.DEPLOYER and bal < int(E_18/2):
                print(f"\n💸 Seeding {addr} with {E_18 - bal} ETH. KERCHINGGG!!\n")
                
                self.DEPLOYER.transfer(addr, E_18 - bal)


    def seed_flip(self, addrs):
        for addr in addrs:
            bal = self.flip.balanceOf(addr)
            if bal < int(MAX_TEST_STAKE/2):
                print(f"\n💸 Seeding {addr} with FLIP. KERCHINGGG!!\n")

                cf.flip.transfer(addr, MAX_TEST_STAKE - bal, {'from': cf.DEPLOYER})


def init_deploy():
    with Chainflip() as cf:
        cf.deploy()


def stake_alice_and_bob():
    with Chainflip() as cf:
        cf.seed_eth([cf.ALICE, cf.BOB])
        cf.seed_flip([cf.ALICE, cf.BOB])

        print(f"\n💰 Staking on behalf of Alice and Bob.\n")
        cf.stakeManager.stake(12321, MIN_STAKE, {'from': cf.ALICE})
        cf.stakeManager.stake(45654, MIN_STAKE + 1, {'from': cf.BOB})
