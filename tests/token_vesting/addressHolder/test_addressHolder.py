from consts import *
from brownie import reverts, chain
from shared_tests_tokenVesting import *


def test_reference_constructor(addrs, cf, AddressHolder):
    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(
            AddressHolder,
            ZERO_ADDR,
            cf.stateChainGateway,
            NON_ZERO_ADDR,
            NON_ZERO_ADDR,
            NON_ZERO_ADDR,
        )

    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(
            AddressHolder,
            NON_ZERO_ADDR,
            ZERO_ADDR,
            NON_ZERO_ADDR,
            NON_ZERO_ADDR,
            NON_ZERO_ADDR,
        )

    # We allow zero addresses to be passed as staking provider references
    addressHolder = addrs.DEPLOYER.deploy(
        AddressHolder, addrs.DEPLOYER, NON_ZERO_ADDR, ZERO_ADDR, ZERO_ADDR, ZERO_ADDR
    )
    assert addressHolder.getGovernor() == addrs.DEPLOYER
    assert addressHolder.getStateChainGateway() == NON_ZERO_ADDR


def test_reference_transferGovernor(addrs, addressHolder):
    with reverts(REV_MSG_SCGREF_REV_GOV):
        addressHolder.transferGovernor(NON_ZERO_ADDR, {"from": addrs.BENEFICIARY})

    with reverts(REV_MSG_NZ_ADDR):
        addressHolder.transferGovernor(ZERO_ADDR, {"from": addrs.DEPLOYER})

    assert addressHolder.getGovernor() == addrs.DEPLOYER
    tx = addressHolder.transferGovernor(NON_ZERO_ADDR, {"from": addrs.DEPLOYER})
    assert tx.events["GovernorTransferred"][0].values() == [
        addrs.DEPLOYER,
        NON_ZERO_ADDR,
    ]
    assert addressHolder.getGovernor() == NON_ZERO_ADDR


def test_reference_updateReference(addrs, cf, addressHolder):
    with reverts(REV_MSG_SCGREF_REV_GOV):
        addressHolder.updateStateChainGateway(
            NON_ZERO_ADDR, {"from": addrs.BENEFICIARY}
        )

    with reverts(REV_MSG_NZ_ADDR):
        addressHolder.updateStateChainGateway(ZERO_ADDR, {"from": addrs.DEPLOYER})

    assert addressHolder.getStateChainGateway() == cf.stateChainGateway
    tx = addressHolder.updateStateChainGateway(NON_ZERO_ADDR, {"from": addrs.DEPLOYER})
    assert tx.events["StateChainGatewayUpdated"][0].values() == [
        cf.stateChainGateway,
        NON_ZERO_ADDR,
    ]
    assert addressHolder.getStateChainGateway() == NON_ZERO_ADDR


def test_reference_release(addrs, cf, tokenVestingStaking, addressHolder):
    tv, _, end, _ = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.BENEFICIARY) == 0

    tv.fundStateChainAccount(JUNK_INT, MAX_TEST_FUND, {"from": addrs.BENEFICIARY})

    chain.sleep(end)

    # Update the refernce to a wrong contract
    addressHolder.updateStateChainGateway(NON_ZERO_ADDR, {"from": addrs.DEPLOYER})

    # Mimic a return of funds from the state chain
    cf.flip.transfer(tv, MAX_TEST_FUND, {"from": addrs.DEPLOYER})

    assert cf.flip.balanceOf(tv) == MAX_TEST_FUND

    tv.release(cf.flip, {"from": addrs.BENEFICIARY})

    assert cf.flip.balanceOf(tv) == 0
    assert cf.flip.balanceOf(addrs.BENEFICIARY) == MAX_TEST_FUND

    # Assert that staking is no longer possible as the reference is wrong.
    # Let's say staking rewards are accrued
    cf.flip.transfer(tv, JUNK_INT, {"from": addrs.DEPLOYER})
    with reverts("Transaction reverted without a reason string"):
        tv.fundStateChainAccount(JUNK_INT, JUNK_INT, {"from": addrs.BENEFICIARY})


def test_reference_updateStakingAddresses(addrs, addressHolder):
    oldAddresses = (
        addressHolder.getStakingAddress(),
        *addressHolder.getUnstakingAddresses(),
    )
    for addresses in [
        (ZERO_ADDR, NON_ZERO_ADDR, NON_ZERO_ADDR),
        (NON_ZERO_ADDR, ZERO_ADDR, NON_ZERO_ADDR),
        (NON_ZERO_ADDR, NON_ZERO_ADDR, ZERO_ADDR),
        (ZERO_ADDR, ZERO_ADDR, ZERO_ADDR),
    ]:
        tx = addressHolder.updateStakingAddresses(*addresses, {"from": addrs.DEPLOYER})
        assert tx.events["StakingAddressesUpdated"][0].values() == (
            *oldAddresses,
            *addresses,
        )
        assert addressHolder.getStakingAddress() == addresses[0]
        assert addressHolder.getUnstakingAddresses() == [addresses[1], addresses[2]]
        oldAddresses = addresses
