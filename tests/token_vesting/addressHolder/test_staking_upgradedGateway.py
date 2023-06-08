from consts import *
from brownie import reverts
from shared_tests_tokenVesting import *
from deploy import deploy_new_stateChainGateway


def test_stake_upgrade_failure(addrs, cf, tokenVestingStaking, scGatewayAddrHolder):
    tv, _, _ = tokenVestingStaking

    tx = tv.fundStateChainAccount(JUNK_HEX, MIN_FUNDING, {"from": addrs.INVESTOR})

    assert tx.events["Funded"][0].values() == (JUNK_HEX, MIN_FUNDING, tv)

    assert cf.flip.balanceOf(tv) > MIN_FUNDING

    scGatewayAddrHolder.updateReferenceAddress(NON_ZERO_ADDR, {"from": addrs.DEPLOYER})

    with reverts("Transaction reverted without a reason string"):
        tv.fundStateChainAccount(JUNK_HEX, MIN_FUNDING, {"from": addrs.INVESTOR})

    scGatewayAddrHolder.updateReferenceAddress(
        cf.stateChainGateway.address, {"from": addrs.DEPLOYER}
    )
    tx = tv.fundStateChainAccount(JUNK_HEX, MIN_FUNDING, {"from": addrs.INVESTOR})
    assert tx.events["Funded"][0].values() == (JUNK_HEX, MIN_FUNDING, tv)


def test_stake_upgrade(
    addrs,
    cf,
    tokenVestingStaking,
    scGatewayAddrHolder,
    KeyManager,
    StateChainGateway,
    FLIP,
    DeployerStateChainGateway,
):
    tv, _, _ = tokenVestingStaking

    tx = tv.fundStateChainAccount(JUNK_HEX, MIN_FUNDING, {"from": addrs.INVESTOR})

    assert tx.events["Funded"][0].values() == (JUNK_HEX, MIN_FUNDING, tv)

    assert cf.flip.balanceOf(tv) > MIN_FUNDING

    (_, newStateChainGateway) = deploy_new_stateChainGateway(
        addrs.DEPLOYER,
        KeyManager,
        StateChainGateway,
        FLIP,
        DeployerStateChainGateway,
        cf.keyManager,
        cf.flip,
        MIN_FUNDING,
    )

    scGatewayAddrHolder.updateReferenceAddress(
        newStateChainGateway.address, {"from": addrs.DEPLOYER}
    )

    tx = tv.fundStateChainAccount(JUNK_HEX, MIN_FUNDING, {"from": addrs.INVESTOR})
    assert tx.events["Funded"][0].values() == (JUNK_HEX, MIN_FUNDING, tv)
