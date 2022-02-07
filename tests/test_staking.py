from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy


@given(
#    nodeID=strategy('bytes32'),
    nodeID=strategy('uint', exclude=0),

    amount=strategy('uint256', max_value=1000*E_18)
)
def test_stake(addrs, tokenVesting, nodeID, amount):

    tv, start, cliff, end, total = tokenVesting

    nodeID = web3.toHex(nodeID)

    if amount < MIN_STAKE:
        with reverts(REV_MSG_MIN_STAKE):
            tx = tv.stake(nodeID, amount, {'from': addrs.INVESTOR})
    else:
        tx = tv.stake(nodeID, amount, {'from': addrs.INVESTOR})
        print(tx.events["Staked"][0].values())
        assert tx.events["Staked"][0].values() == ('0x'+nodeID.hex(), amount, tv)


def test_stake_rev_beneficiary(a, addrs, tokenVesting):
    tv, start, cliff, end, total = tokenVesting

    for ad in a:
        if ad != addrs.INVESTOR:
            with reverts("TokenVesting: not the beneficiary"):    
                tv.stake(5, 10, {'from': ad})


def test_stake_rev_cannot_stake(a, addrs, mockSM, TokenVesting):
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
        mockSM
    )
    
    with reverts("TokenVesting: cannot stake"):    
        tv.stake(5, 10, {'from': addrs.INVESTOR})