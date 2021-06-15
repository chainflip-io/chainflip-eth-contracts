from contextlib import contextmanager
from brownie import chain, accounts, KeyManager, Vault, StakeManager, FLIP

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

        self.DEPLOYER = accounts[0]
        self.ALICE = accounts[1]
        self.BOB = accounts[2]
        self.CHARLIE = accounts[3]
        self.DENICE = accounts[4]

        self.keyManager = None
        self.vault = None
        self.stakeManager = None
        self.flip = None

    def __enter__(self):
        if not self.deployed:
            self.deploy()
            chain.snapshot()
        
        return self
    
    def __exit__(self, *args):
        # chain.revert()
        pass
    
    def deploy(self):
        print(f"\n💾 Deploying chainflip contracts in {path.abspath((path.curdir))}\n")
        
        self.keyManager = self.DEPLOYER.deploy(KeyManager, AGG_SIGNER_1.getPubData(), GOV_SIGNER_1.getPubData())
        self.vault = self.DEPLOYER.deploy(Vault, self.keyManager)
        self.stakeManager = self.DEPLOYER.deploy(StakeManager, self.keyManager, EMISSION_PER_BLOCK, MIN_STAKE, INIT_SUPPLY)
        self.flip = FLIP.at(self.stakeManager.getFLIPAddress())

        self.deployed = True

        print("========================= 😎  Deployed! 😎 ==========================\n")
        print(f"StakeManager deployed by {self.DEPLOYER} to address: {StakeManager[0]}\n")
        print("====================================================================")
    
    def seed_flip(self, addrs):
        for addr in addrs:
            print(f"\n💸 Seeding {addr} with FLIP. KERCHINGGG!!\n")

            self.flip.transfer(addr, MAX_TEST_STAKE, {'from': self.DEPLOYER})


def stake_alice_and_bob():
    with Chainflip() as cf:
        cf.seed_flip([cf.ALICE, cf.BOB])

        print(f"\n💰 Staking on behalf of Alice and Bob.\n")
        cf.stakeManager.stake(12321, MIN_STAKE, NON_ZERO_ADDR, {'from': cf.ALICE})
        cf.stakeManager.stake(45654, MIN_STAKE + 1, NON_ZERO_ADDR, {'from': cf.BOB})
