from consts import *
from brownie import reverts, chain
from shared_tests_tokenVesting import *


def test_reference_constructor(addrs, cf, AddressHolder):
    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(AddressHolder, ZERO_ADDR, cf.stateChainGateway)

    with reverts(REV_MSG_NZ_ADDR):
        addrs.DEPLOYER.deploy(AddressHolder, NON_ZERO_ADDR, ZERO_ADDR)

    addressHolder = addrs.DEPLOYER.deploy(AddressHolder, addrs.DEPLOYER, NON_ZERO_ADDR)
    assert addressHolder.getGovernor() == addrs.DEPLOYER
    assert addressHolder.getReferenceAddress() == NON_ZERO_ADDR


def test_reference_transferGovernor(addrs, addressHolder):
    with reverts(REV_MSG_SCGREF_REV_GOV):
        addressHolder.transferGovernor(NON_ZERO_ADDR, {"from": addrs.INVESTOR})

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
        addressHolder.updateReferenceAddress(NON_ZERO_ADDR, {"from": addrs.INVESTOR})

    with reverts(REV_MSG_NZ_ADDR):
        addressHolder.updateReferenceAddress(ZERO_ADDR, {"from": addrs.DEPLOYER})

    assert addressHolder.getReferenceAddress() == cf.stateChainGateway
    tx = addressHolder.updateReferenceAddress(NON_ZERO_ADDR, {"from": addrs.DEPLOYER})
    assert tx.events["ReferenceAddressUpdated"][0].values() == [
        cf.stateChainGateway,
        NON_ZERO_ADDR,
    ]
    assert addressHolder.getReferenceAddress() == NON_ZERO_ADDR


def test_reference_release(addrs, cf, tokenVestingStaking, addressHolder):
    tv, _, _, _ = tokenVestingStaking

    assert cf.flip.balanceOf(addrs.INVESTOR) == 0

    tv.fundStateChainAccount(JUNK_INT, MAX_TEST_FUND, {"from": addrs.INVESTOR})

    chain.sleep(YEAR + QUARTER_YEAR)

    # Update the refernce to a wrong contract
    addressHolder.updateReferenceAddress(NON_ZERO_ADDR, {"from": addrs.DEPLOYER})

    # Mimic a return of funds from the state chain
    cf.flip.transfer(tv, MAX_TEST_FUND, {"from": addrs.DEPLOYER})

    assert cf.flip.balanceOf(tv) == MAX_TEST_FUND

    tv.release(cf.flip, {"from": addrs.INVESTOR})

    assert cf.flip.balanceOf(tv) == 0
    assert cf.flip.balanceOf(addrs.INVESTOR) == MAX_TEST_FUND

    # Assert that staking is no longer possible as the reference is wrong.
    # Let's say staking rewards are accrued
    cf.flip.transfer(tv, JUNK_INT, {"from": addrs.DEPLOYER})
    with reverts("Transaction reverted without a reason string"):
        tv.fundStateChainAccount(JUNK_INT, JUNK_INT, {"from": addrs.INVESTOR})
