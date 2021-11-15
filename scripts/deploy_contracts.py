import sys
import os
sys.path.append(os.path.abspath('tests'))
from consts import *
from brownie import chain, accounts, KeyManager, Vault, StakeManager, FLIP
from deploy import deploy_set_Chainflip_contracts



def main():
    AUTONOMY_SEED = os.environ['SEED']
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)

    DEPLOYER = cf_accs[0]
    print(f'DEPLOYER = {DEPLOYER}')

    cf = deploy_set_Chainflip_contracts(DEPLOYER, KeyManager, Vault, StakeManager, FLIP, os.environ)

    print(f'FLIP = {cf.stakeManager.getFLIP()}')