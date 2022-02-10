from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy


@given(
    nodeID=strategy('uint', exclude=0),
    amount=strategy('uint256', max_value=MAX_TEST_STAKE)
)
def test_stake_nonstakable(addrs, tokenVestingNoStaking, nodeID, amount):

    tv, start, cliff, end, total = tokenVestingNoStaking

    nodeID = web3.toHex(nodeID)

    with reverts(REV_MSG_CANNOT_STAKE):
        tx = tv.stake(nodeID, amount, {'from': addrs.INVESTOR})


@given(
    nodeID=strategy('uint', exclude=0),
    amount=strategy('uint256', max_value=MAX_TEST_STAKE*2)
)
def test_stake(addrs, tokenVestingStaking, nodeID, amount, cf):

    tv, start, cliff, end, total = tokenVestingStaking

    nodeID = web3.toHex(nodeID)
   
    if amount < MIN_STAKE:
        with reverts(REV_MSG_MIN_STAKE):
            tx = tv.stake(nodeID, amount, {'from': addrs.INVESTOR})
    elif amount > cf.flip.balanceOf(tv):
        with reverts("ERC777: transfer amount exceeds balance"):
            tx = tv.stake(nodeID, amount, {'from': addrs.INVESTOR})        
    else:       
        tx = tv.stake(nodeID, amount, {'from': addrs.INVESTOR})

        assert tx.events["Staked"][0].values() == (nodeID, amount, tv, tv)
        
def test_stake_rev_beneficiary(a, addrs, tokenVestingStaking):
    tv, start, cliff, end, total = tokenVestingStaking

    for ad in a:
        if ad != addrs.INVESTOR:
            with reverts("TokenVesting: not the beneficiary"):    
                tv.stake(5, 10, {'from': ad})



