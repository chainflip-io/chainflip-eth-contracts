from consts import *
from shared_tests import *
from brownie import reverts, web3
from brownie.test import given, strategy


def test_claimBatch(cf, stakedMin):
    # Want to calculate inflation 1 block into the future because that's when the tx will execute
    newLastMintBlockNum = web3.eth.blockNumber + 1
    inflation = getInflation(cf.stakeManager.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)
    nodeIDs = [2, 3]
    receivers = [cf.CHARLIE, cf.DENICE]
    amounts = [MIN_STAKE, 1]
    totalAmount = sum(amounts)

    # More than MIN_STAKE can be claimed straight away for sure because of inflation
    callDataNoSig = cf.stakeManager.claimBatch.encode_input(NULL_SIG_DATA, nodeIDs, receivers, amounts)
    tx = cf.stakeManager.claimBatch(AGG_SIGNER_1.getSigData(callDataNoSig), nodeIDs, receivers, amounts)

    # Check things that should've changed
    assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + inflation - totalAmount
    assert cf.stakeManager.getLastMintBlockNum() == tx.block_number
    assert cf.stakeManager.getTotalStakeInFuture(0) == MIN_STAKE + inflation - totalAmount
    assert tx.events["Transfer"][0].values() == [ZERO_ADDR, cf.stakeManager.address, inflation]
    assert len(tx.events["Transfer"]) == len(amounts) + 1
    assert len(tx.events["Claimed"]) == len(amounts)
    for i in range(len(receivers)):
        assert cf.flip.balanceOf(receivers[i]) == amounts[i]
        assert tx.events["Claimed"][i].values() == [nodeIDs[i], amounts[i]]
    
    # Check things that shouldn't have changed
    assert cf.stakeManager.getEmissionPerBlock() == EMISSION_PER_BLOCK
    assert cf.stakeManager.getMinimumStake() == MIN_STAKE


@given(
    nodeIDs=strategy('uint256[5]'),
    amounts=strategy('uint256[5]', max_value=MIN_STAKE*2),
    receivers=strategy('address[5]', unique=True)
)
def test_claimBatch_rand(cf, stakedMin, nodeIDs, amounts, receivers):
    # Want to calculate inflation 1 block into the future because that's when the tx will execute
    newLastMintBlockNum = web3.eth.blockNumber + 1
    inflation = getInflation(cf.stakeManager.tx.block_number, newLastMintBlockNum, EMISSION_PER_BLOCK)
    totalAmount = sum(amounts)
    prevBals = [cf.flip.balanceOf(r) for r in receivers]

    callDataNoSig = cf.stakeManager.claimBatch.encode_input(NULL_SIG_DATA, nodeIDs, receivers, amounts)

    if totalAmount > cf.flip.balanceOf(cf.stakeManager) + inflation:
        with reverts(REV_MSG_EXCEED_BAL):
            tx = cf.stakeManager.claimBatch(AGG_SIGNER_1.getSigData(callDataNoSig), nodeIDs, receivers, amounts)
    else:
        tx = cf.stakeManager.claimBatch(AGG_SIGNER_1.getSigData(callDataNoSig), nodeIDs, receivers, amounts)

        # Check things that should've changed
        assert cf.flip.balanceOf(cf.stakeManager) == MIN_STAKE + inflation - totalAmount
        assert cf.stakeManager.getLastMintBlockNum() == tx.block_number
        assert cf.stakeManager.getTotalStakeInFuture(0) == MIN_STAKE + inflation - totalAmount
        assert tx.events["Transfer"][0].values() == [ZERO_ADDR, cf.stakeManager.address, inflation]
        assert len(tx.events["Transfer"]) == len(amounts) + 1
        assert len(tx.events["Claimed"]) == len(amounts)
        for i in range(len(receivers)):
            assert cf.flip.balanceOf(receivers[i]) == prevBals[i] + amounts[i]
            assert tx.events["Claimed"][i].values() == [nodeIDs[i], amounts[i]]
        
        # Check things that shouldn't have changed
        assert cf.stakeManager.getEmissionPerBlock() == EMISSION_PER_BLOCK
        assert cf.stakeManager.getMinimumStake() == MIN_STAKE


def test_claimBatch_rev_sig(cf, stakedMin):
    nodeIDs = [2, 3]
    receivers = [cf.CHARLIE, cf.DENICE]
    amounts = [MIN_STAKE, 1]
    callDataNoSig = cf.stakeManager.claimBatch.encode_input(NULL_SIG_DATA, nodeIDs, receivers, amounts)

    with reverts(REV_MSG_SIG):
        cf.stakeManager.claimBatch(AGG_SIGNER_2.getSigData(callDataNoSig), nodeIDs, receivers, amounts)


def test_claimBatch_rev_arr_len(cf, stakedMin):
    nodeIDs = [2, 3, 4]
    receivers = [cf.CHARLIE, cf.DENICE]
    amounts = [MIN_STAKE, 1]
    callDataNoSig = cf.stakeManager.claimBatch.encode_input(NULL_SIG_DATA, nodeIDs, receivers, amounts)

    with reverts(REV_MSG_SM_ARR_LEN):
        cf.stakeManager.claimBatch(AGG_SIGNER_1.getSigData(callDataNoSig), nodeIDs, receivers, amounts)


# Can't use the normal StakeManager to test this since there's obviously
# intentionally no way to get FLIP out of the contract without calling `claim`,
# so we have to use StakeManagerVulnerable which inherits StakeManager and
# has `testSendFLIP` in it to simulate some kind of hack
@given(
    nodeIDs=strategy('uint256[5]'),
    amounts=strategy('uint256[5]', max_value=MIN_STAKE),
    receivers=strategy('address[5]', unique=True)
)
def test_claimBatch_rev_noFish(cf, vulnerableR3ktStakeMan, nodeIDs, receivers, amounts):
    smVuln, flipVuln = vulnerableR3ktStakeMan
    totalAmount = sum(amounts)

    callDataNoSig = smVuln.claimBatch.encode_input(NULL_SIG_DATA, nodeIDs, receivers, amounts)

    print(flipVuln.balanceOf(smVuln))
    if sum(amounts) > flipVuln.balanceOf(smVuln):
        with reverts(REV_MSG_EXCEED_BAL):
            smVuln.claimBatch(AGG_SIGNER_1.getSigData(callDataNoSig), nodeIDs, receivers, amounts)
    else:
        with reverts(REV_MSG_NO_FISH):
            smVuln.claimBatch(AGG_SIGNER_1.getSigData(callDataNoSig), nodeIDs, receivers, amounts)