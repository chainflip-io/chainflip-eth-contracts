from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
import pytest

### Release Shared Tests

def release_revert(tv, cf, address):
    with reverts(REV_MSG_NO_TOKENS):
        tv.release(cf.flip, {'from': address})


def check_released (tv, cf, tx, address, totalReleased, recentlyReleased):
        # Using float conversion and pytest bc of python comparison limitations w big numbers
        assert float(cf.flip.balanceOf(address)) == float(totalReleased)
        assert float(tv.released(cf.flip)) == float(totalReleased)
        assert tx.events["TokensReleased"][0].values()[0] == cf.flip
        assert float(tx.events["TokensReleased"][0].values()[1]) == pytest.approx(recentlyReleased)


def check_state (tv, cf, beneficiary, revoker, revocable, cliff, end, canStake, stakeManager, revoked  ):
        assert tv.beneficiary() == beneficiary
        assert tv.revoker() == revoker
        assert tv.revocable() == revocable
        assert tv.cliff() == cliff
        assert tv.end() == end
        assert tv.canStake() == canStake
        assert tv.stakeManager() == stakeManager
        assert tv.revoked(cf.flip) == revoked


### Revoked Shared Tests

def check_revoked (tv, cf, tx, address, revokedAmount, amountLeft):
        # Using float conversion and pytest bc of python comparison limitations w big numbers
        assert float(cf.flip.balanceOf(address)) == pytest.approx(revokedAmount)
        assert float(cf.flip.balanceOf(tv)) == pytest.approx(amountLeft)
        assert tx.events["TokenVestingRevoked"][0].values() == [cf.flip]

def retrieve_revoked_and_check (tv, cf, address, retrievedAmount):        
        # Using float conversion and pytest bc of python comparison limitations w big numbers
        initialBalance = cf.flip.balanceOf(address)
        tx = tv.retrieveRevokedFunds(cf.flip, {'from': address})
        finalBalance = cf.flip.balanceOf(address)

        assert retrievedAmount == finalBalance - initialBalance

        assert float(cf.flip.balanceOf(address)) == pytest.approx(initialBalance + retrievedAmount)
        assert float(cf.flip.balanceOf(tv)) == pytest.approx(0)
        assert tx.events["Transfer"][0].values() == (tv,address, retrievedAmount)