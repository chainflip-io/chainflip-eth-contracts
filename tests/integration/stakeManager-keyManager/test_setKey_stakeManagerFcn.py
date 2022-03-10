from consts import *
from shared_tests import *
from brownie import reverts, web3


def test_setAggKeyWithAggKey_updateFlipSupply(cfAW):
    # Change agg keys
    setAggKeyWithAggKey_test(cfAW)

    stateChainBlockNumber = 1

    callDataNoSig = cfAW.stakeManager.updateFlipSupply.encode_input(
        agg_null_sig(cfAW.keyManager.address, chain.id),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    )

    # Changing emission with old key should revert
    with reverts(REV_MSG_SIG):
        cfAW.stakeManager.updateFlipSupply(
            AGG_SIGNER_1.getSigData(callDataNoSig, cfAW.keyManager.address),
            NEW_TOTAL_SUPPLY_MINT,
            stateChainBlockNumber,
            cfAW.FR_ALICE,
        )

    # Change emission with new key
    callDataNoSig = cfAW.stakeManager.updateFlipSupply.encode_input(
        agg_null_sig(cfAW.keyManager.address, chain.id),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    )
    tx = cfAW.stakeManager.updateFlipSupply(
        AGG_SIGNER_2.getSigData(callDataNoSig, cfAW.keyManager.address),
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
        cfAW.FR_ALICE,
    )

    # Check things that should've changed
    assert cfAW.flip.totalSupply() == NEW_TOTAL_SUPPLY_MINT
    assert (
        cfAW.flip.balanceOf(cfAW.stakeManager)
        == NEW_TOTAL_SUPPLY_MINT - INIT_SUPPLY + STAKEMANAGER_INITIAL_BALANCE
    )
    assert cfAW.stakeManager.getLastSupplyUpdateBlockNumber() == stateChainBlockNumber
    assert tx.events["FlipSupplyUpdated"][0].values() == [
        INIT_SUPPLY,
        NEW_TOTAL_SUPPLY_MINT,
        stateChainBlockNumber,
    ]

    # Check things that shouldn't have changed
    assert cfAW.stakeManager.getMinimumStake() == MIN_STAKE


def test_setGovKeyWithGovKey_setMinStake(cfAW):
    # Change agg keys
    setGovKeyWithGovKey_test(cfAW)

    newMinStake = int(MIN_STAKE * 1.5)

    # Changing emission with old key should revert
    with reverts(REV_MSG_STAKEMAN_GOVERNOR):
        cfAW.stakeManager.setMinStake(newMinStake, {"from": cfAW.GOVERNOR})

    # Change minStake with new key
    tx = cfAW.stakeManager.setMinStake(newMinStake, {"from": cfAW.GOVERNOR_2})

    # Check things that should've changed
    assert cfAW.stakeManager.getMinimumStake() == newMinStake
    assert tx.events["MinStakeChanged"][0].values() == [MIN_STAKE, newMinStake]

    # Check things that shouldn't have changed
    assert cfAW.flip.balanceOf(cfAW.stakeManager) == STAKEMANAGER_INITIAL_BALANCE
