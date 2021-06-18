from consts import *
from brownie.test import given, strategy


# `\EMISSION_PER_BLOCK` is so that the fcn doesn't overflow
# `255` rather than 256 is accout for some already-mined blocks
@given(blocksIntoFuture=strategy('uint256', max_value=int((2**256)/EMISSION_PER_BLOCK)))
def test_getTotalStakeInFuture(cf, stakedMin, web3, blocksIntoFuture):
    _, amount = stakedMin
    initBlockNum = cf.stakeManager.tx.block_number
    currentBlockNum = web3.eth.block_number
    assert cf.stakeManager.getTotalStakeInFuture(blocksIntoFuture) == \
        amount + getInflation(initBlockNum, currentBlockNum + blocksIntoFuture, EMISSION_PER_BLOCK)
