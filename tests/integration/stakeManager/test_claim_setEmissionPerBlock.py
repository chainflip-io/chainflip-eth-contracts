from consts import *
from shared_tests import *
from brownie import web3, chain


def test_registerClaim_setEmissionPerBlock_executeClaim(cf, stakedMin):
    _, amountStaked = stakedMin
    emissionPerBlock1 = EMISSION_PER_BLOCK
    claimAmount = amountStaked
    emissionPerBlock2 = int(EMISSION_PER_BLOCK * 1.5)
    receiver = cf.DENICE

    registerClaimTest(
        cf,
        cf.stakeManager.tx,
        amountStaked,
        JUNK_INT,
        EMISSION_PER_BLOCK,
        MIN_STAKE,
        claimAmount,
        receiver,
        chain.time() + (2 * CLAIM_DELAY)
    )

    callDataNoSig = cf.stakeManager.setEmissionPerBlock.encode_input(NULL_SIG_DATA, emissionPerBlock2)
    emissionTx1 = cf.stakeManager.setEmissionPerBlock(GOV_SIGNER_1.getSigData(callDataNoSig), emissionPerBlock2, {"from": cf.ALICE})
    
    # Check things that should've changed
    inflation1 = getInflation(cf.stakeManager.tx.blockNumber, emissionTx1.blockNumber, EMISSION_PER_BLOCK)
    assert cf.flip.balanceOf(cf.stakeManager) == amountStaked + inflation1
    assert cf.stakeManager.getInflationInFuture(0) == 0
    assert cf.stakeManager.getTotalStakeInFuture(0) == amountStaked + inflation1
    assert cf.stakeManager.getEmissionPerBlock() == emissionPerBlock2
    assert cf.stakeManager.getLastMintBlockNum() == emissionTx1.blockNumber
    assert emissionTx1.events["EmissionChanged"][0].values() == [EMISSION_PER_BLOCK, emissionPerBlock2]
    # Check things that shouldn't have changed
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE

    # Want to calculate inflation 1 block into the future because that's when the tx will execute
    inflation2 = getInflation(emissionTx1.blockNumber, web3.eth.blockNumber + 1, emissionPerBlock2)

    chain.sleep(CLAIM_DELAY + 5)
    execTx = cf.stakeManager.executeClaim(JUNK_INT)

    # Check things that should've changed
    assert cf.stakeManager.getPendingClaim(JUNK_INT) == NULL_CLAIM
    assert cf.stakeManager.getLastMintBlockNum() == execTx.blockNumber
    assert cf.flip.balanceOf(cf.stakeManager) == amountStaked + inflation1 + inflation2 - claimAmount
    assert cf.stakeManager.getTotalStakeInFuture(0) == amountStaked + inflation1 + inflation2 - claimAmount
    assert execTx.events["ClaimExecuted"][0].values() == [JUNK_INT, claimAmount]
    assert cf.flip.balanceOf(receiver) == claimAmount
    # Check things that shouldn't have changed
    assert cf.stakeManager.getEmissionPerBlock() == emissionPerBlock2
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE