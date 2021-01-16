from consts import *
from brownie import reverts
from shared_tests import *


def test_setAggKeyWithAggKey(cf):
    setAggKeyWithAggKey_test(cf)


def test_setAggKeyWithGovKey(cf):
    setAggKeyWithGovKey_test(cf)


def test_setGovKeyWithGovKey(cf):
    setGovKeyWithGovKey_test(cf)
