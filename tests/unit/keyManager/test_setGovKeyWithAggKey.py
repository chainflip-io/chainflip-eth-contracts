from consts import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy
from utils import *
from shared_tests import *


def test_setGovKeyWithAggKey(cf):
    setGovKeyWithAggKey_test(cf)
