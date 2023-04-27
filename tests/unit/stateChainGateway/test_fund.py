from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
from utils import *


@given(st_amount=strategy("uint256", max_value=MAX_TEST_FUND))
def test_fund_st_amount_rand(cf, st_amount):
    if st_amount < MIN_FUNDING:
        with reverts(REV_MSG_MIN_FUNDING):
            cf.flip.approve(cf.stateChainGateway.address, st_amount, {"from": cf.ALICE})
            cf.stateChainGateway.fundStateChainAccount(
                JUNK_HEX, st_amount, {"from": cf.ALICE}
            )
    else:
        cf.flip.approve(cf.stateChainGateway.address, st_amount, {"from": cf.ALICE})
        tx = cf.stateChainGateway.fundStateChainAccount(
            JUNK_HEX, st_amount, {"from": cf.ALICE}
        )
        fundTest(cf, 0, JUNK_HEX, MIN_FUNDING, tx, st_amount)


def test_fund_min(cf, fundedMin):
    tx, amount = fundedMin
    fundTest(cf, 0, JUNK_HEX, MIN_FUNDING, tx, amount)


def test_fund_rev_st_amount_just_under_minFunding(cf):
    with reverts(REV_MSG_MIN_FUNDING):
        cf.flip.approve(
            cf.stateChainGateway.address, MIN_FUNDING - 1, {"from": cf.ALICE}
        )
        cf.stateChainGateway.fundStateChainAccount(
            JUNK_HEX, MIN_FUNDING - 1, {"from": cf.ALICE}
        )


def test_fund_rev_nodeID(cf):
    with reverts(REV_MSG_NZ_BYTES32):
        cf.stateChainGateway.fundStateChainAccount(
            0,
            cf.stateChainGateway.getMinimumFunding(),
            {"from": cf.ALICE},
        )
