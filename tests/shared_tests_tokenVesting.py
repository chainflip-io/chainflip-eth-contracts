from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
import pytest

### Release Shared Tests


def release_revert(tv, cf, address):
    with reverts(REV_MSG_NO_TOKENS):
        tv.release(cf.flip, {"from": address})


def check_released(tv, cf, tx, address, totalReleased, recentlyReleased):
    assert cf.flip.balanceOf(address) == totalReleased
    assert tv.released(cf.flip) == totalReleased
    assert tx.events["TokensReleased"][0].values()[0] == cf.flip
    assert tx.events["TokensReleased"][0].values()[1] == recentlyReleased


def check_state_staking(stateChainGateway, addressHolder, tv, cf, *args):

    assert tv.addressHolder() == addressHolder
    assert addressHolder.getStateChainGateway() == stateChainGateway
    check_state(tv, cf, *args)


def check_state_noStaking(cliff, tv, *args):

    assert tv.cliff() == cliff
    check_state(tv, *args)


def check_state(
    tv,
    cf,
    beneficiary,
    revoker,
    revocable,
    end,
    transferableBeneficiary,
    revoked,
):
    assert tv.getBeneficiary() == beneficiary
    assert tv.getRevoker() == revoker
    tv_revocable = tv.getRevoker() != ZERO_ADDR
    assert tv_revocable == revocable
    assert tv.end() == end
    assert tv.transferableBeneficiary() == transferableBeneficiary

    assert tv.revoked(cf.flip) == revoked


### Revoked Shared Tests


def check_revoked(tv, cf, tx, address, revokedAmount, amountLeft):
    assert cf.flip.balanceOf(address) == revokedAmount
    assert cf.flip.balanceOf(tv) == amountLeft
    assert tx.events["TokenVestingRevoked"][0].values() == [cf.flip, revokedAmount]


def retrieve_revoked_and_check(tv, cf, address, retrievedAmount):
    initialBalance = cf.flip.balanceOf(address)
    tx = tv.retrieveRevokedFunds(cf.flip, {"from": address})
    finalBalance = cf.flip.balanceOf(address)

    assert retrievedAmount == finalBalance - initialBalance

    assert cf.flip.balanceOf(address) == initialBalance + retrievedAmount
    assert cf.flip.balanceOf(tv) == 0
    assert tx.events["Transfer"][0].values() == (tv, address, retrievedAmount)
