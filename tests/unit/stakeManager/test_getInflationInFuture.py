from consts import *
from brownie.test import given, strategy


# `\EMISSION_PER_BLOCK` is so that the fcn doesn't overflow
# `255` rather than 256 is accout for some already-mined blocks
@given(blocksIntoFuture=strategy('uint256', max_value=int((2**255)/EMISSION_PER_BLOCK)))
def test_getInflationInFuture(cf, web3, blocksIntoFuture):
    initBlockNum = cf.stakeManager.tx.block_number
    currentBlockNum = web3.eth.blockNumber
    assert cf.stakeManager.getInflationInFuture(blocksIntoFuture) == \
        getInflation(initBlockNum, currentBlockNum + blocksIntoFuture, EMISSION_PER_BLOCK)
