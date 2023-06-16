from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *


@given(st_sender=strategy("address"))
def test_transfer_revoker(addrs, tokenVestingStaking, tokenVestingNoStaking, st_sender):
    tv_staking, _, _ = tokenVestingStaking
    tv_noStaking, _, _, _ = tokenVestingNoStaking

    for vestingContract in [tv_staking, tv_noStaking]:
        assert vestingContract.getRevoker() == addrs.REVOKER

        if st_sender != addrs.REVOKER:
            with reverts(REV_MSG_NOT_REVOKER):
                vestingContract.transferRevoker(st_sender, {"from": st_sender})

            tx = vestingContract.transferRevoker(st_sender, {"from": addrs.REVOKER})
            assert vestingContract.getRevoker() == st_sender
            assert tx.events["RevokerTransferred"][0].values() == [
                addrs.REVOKER,
                st_sender,
            ]
