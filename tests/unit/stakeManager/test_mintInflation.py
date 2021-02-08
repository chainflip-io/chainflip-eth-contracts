from consts import *
from brownie.test import given, strategy
from brownie import chain


# def inflationTest(cf, startBlock, currentBlock, pastInflation):
#     inflation = getInflation(startBlock, currentBlock, EMISSION_PER_BLOCK)
#     assert cf.stakeManager.getInflationInFuture(0) == inflation
#     assert cf.stakeManager.getTotalStakeInFuture(0) == MIN_STAKE + inflation
#     assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + inflation + pastInflation
#     assert cf.stakeManager.getLastMintBlockNum() == currentBlock

#     return inflation



# Since _mintInflation is private, need to use setEmissionPerBlock to test it
@given(blocks=strategy('uint256', max_value=10))
def test_mintInflation(cf, stakedMin, web3, blocks):
    chain.mine(blocks)
    initBlockNum = cf.stakeManager.tx.block_number

    inflation = getInflation(initBlockNum, web3.eth.blockNumber+1, EMISSION_PER_BLOCK)
    assert cf.stakeManager.getInflationInFuture(1) == inflation
    assert cf.stakeManager.getTotalStakeInFuture(1) == MIN_STAKE + inflation
    assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE
    assert cf.stakeManager.getLastMintBlockNum() == initBlockNum

    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(NULL_SIG_DATA, EMISSION_PER_BLOCK)
    tx = cf.stakeManager.setEmissionPerBlock(GOV_SIGNER_1.getSigData(callDataNoSig), EMISSION_PER_BLOCK, {"from": cf.ALICE})

    assert cf.stakeManager.getInflationInFuture(0) == 0
    assert cf.stakeManager.getTotalStakeInFuture(0) == MIN_STAKE + inflation
    assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + inflation
    assert cf.stakeManager.getLastMintBlockNum() == tx.block_number

    chain.mine(blocks)

    inflation2 = getInflation(tx.block_number, web3.eth.blockNumber+1, EMISSION_PER_BLOCK)
    assert cf.stakeManager.getInflationInFuture(1) == inflation2
    assert cf.stakeManager.getTotalStakeInFuture(1) == MIN_STAKE + inflation + inflation2
    assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + inflation
    assert cf.stakeManager.getLastMintBlockNum() == tx.block_number

    tx2 = cf.stakeManager.setEmissionPerBlock(GOV_SIGNER_1.getSigData(callDataNoSig), EMISSION_PER_BLOCK, {"from": cf.ALICE})

    assert cf.stakeManager.getInflationInFuture(0) == 0
    assert cf.stakeManager.getTotalStakeInFuture(0) == MIN_STAKE + inflation + inflation2
    assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + inflation + inflation2
    assert cf.stakeManager.getLastMintBlockNum() == tx2.block_number


    # test transfer event