from consts import *
from shared_tests import *
from brownie import web3


def test_claim_setEmissionPerBlock_claim(cf, stakedMin):
    _, amountStaked = stakedMin
    emissionPerBlock1 = EMISSION_PER_BLOCK
    claimAmount1 = amountStaked
    emissionPerBlock2 = int(EMISSION_PER_BLOCK * 1.5)
    receiver = cf.DENICE

    claimTx1, inflation1 = claimTest(
        cf,
        web3,
        cf.stakeManager.tx,
        amountStaked,
        JUNK_INT,
        EMISSION_PER_BLOCK,
        MIN_STAKE,
        claimAmount1,
        receiver,
        0
    )
    assert claimTx1 is not None

    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(NULL_SIG_DATA, emissionPerBlock2)
    emissionTx1 = cf.stakeManager.setEmissionPerBlock(GOV_SIGNER_1.getSigData(callDataNoSig), emissionPerBlock2, {"from": cf.ALICE})
    
    # Check things that should've changed
    inflation2 = getInflation(claimTx1.block_number, emissionTx1.block_number, EMISSION_PER_BLOCK)
    assert cf.flip.balanceOf(cf.stakeManager) == inflation1 + inflation2
    assert cf.stakeManager.getInflationInFuture(0) == 0
    assert cf.stakeManager.getTotalStakeInFuture(0) == inflation1 + inflation2
    assert cf.stakeManager.getEmissionPerBlock() == emissionPerBlock2
    assert cf.stakeManager.getLastMintBlockNum() == emissionTx1.block_number
    assert emissionTx1.events["EmissionChanged"][0].values() == [EMISSION_PER_BLOCK, emissionPerBlock2]
    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE

    calcInflation3 = getInflation(emissionTx1.block_number, web3.eth.blockNumber + 1, emissionPerBlock2)

    claimTx2, inflation3 = claimTest(
        cf,
        web3,
        emissionTx1,
        inflation1 + inflation2,
        JUNK_INT,
        emissionPerBlock2,
        MIN_STAKE,
        inflation1 + inflation2 + calcInflation3,
        receiver,
        claimAmount1
    )
    assert claimTx1 is not None

    assert calcInflation3 == inflation3
    assert cf.flip.balanceOf(cf.DENICE) == MIN_STAKE + inflation1 + inflation2 + inflation3