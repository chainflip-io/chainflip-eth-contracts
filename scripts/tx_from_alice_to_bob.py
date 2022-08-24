import sys
from os import path

sys.path.append(path.abspath("tests"))
from brownie import (
    accounts,
    network,
)


def main():
    ALICE = accounts[1]
    BOB = accounts[2]

    ALICE.transfer(BOB, "0.1 ether", priority_fee="2 gwei")
