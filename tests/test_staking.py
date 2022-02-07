from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy


@given(
    nodeID=strategy('uint', exclude=0),
    amount=strategy('uint256', max_value=MAX_TEST_STAKE)
)
def test_stake(addrs, tokenVesting, nodeID, amount):

    tv, start, cliff, end, total = tokenVesting

    nodeID = web3.toHex(nodeID)

    if amount < MIN_STAKE:
        with reverts(REV_MSG_MIN_STAKE):
            tx = tv.stake(nodeID, amount, {'from': addrs.INVESTOR})
    else:       
        tx = tv.stake(nodeID, amount, {'from': addrs.INVESTOR})
        assert tx.events["Staked"][0].values()[1] == amount
        assert tx.events["Staked"][0].values()[2] == tv

def test_stake_rev_beneficiary(a, addrs, tokenVesting):
    tv, start, cliff, end, total = tokenVesting

    for ad in a:
        if ad != addrs.INVESTOR:
            with reverts("TokenVesting: not the beneficiary"):    
                tv.stake(5, 10, {'from': ad})


def test_stake_rev_cannot_stake(a, addrs, TokenVesting, cf):
    start = 1622400000
    cliff = start + QUARTER_YEAR
    end = start + QUARTER_YEAR + YEAR
    
    tv = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        True,
        start,
        cliff,
        end,
        False,
        cf.stakeManager
    )
    
    with reverts("TokenVesting: cannot stake"):    
        tv.stake(5, 10, {'from': addrs.INVESTOR})