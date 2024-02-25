import sys
import os

sys.path.append(os.path.abspath("tests"))
from shared_tests import *
from consts import *
from brownie import accounts, network

AUTONOMY_SEED = os.environ["SEED"]
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
# Use the second account for the initial spamming
DEPLOYER_ACCOUNT_INDEX = 1

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {DEPLOYER}")
network.priority_fee("1 gwei")

# NUM_SPAM_TXS = int(os.environ["NUM_SPAM_TXS"])
NUM_SPAM_TXS = 100


def main():
    for i in range(NUM_SPAM_TXS):
        DEPLOYER.transfer(DEPLOYER, "1 ether")
