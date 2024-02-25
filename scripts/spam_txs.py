import sys
import os

sys.path.append(os.path.abspath("tests"))
from shared_tests import *
from utils import prompt_user_continue_or_break
from consts import *
from brownie import accounts, network

AUTONOMY_SEED = os.environ["SEED"]
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 1)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {DEPLOYER}")
network.priority_fee("1 gwei")

# NUM_SPAM_TXS = int(os.environ["NUM_SPAM_TXS"])
NUM_SPAM_TXS = 100

print("DEPLOYER", DEPLOYER)


def main():
    for i in range(NUM_SPAM_TXS):
        DEPLOYER.transfer(DEPLOYER, "1 ether")
