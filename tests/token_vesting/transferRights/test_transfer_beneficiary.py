from consts import *
from brownie import reverts, chain
from brownie.test import given, strategy
from shared_tests_tokenVesting import *


@given(st_sender=strategy("address"))
def test_transfer_beneficiary(
    addrs, tokenVestingStaking, tokenVestingNoStaking, st_sender
):
    tv_staking, _, _, _ = tokenVestingStaking
    tv_noStaking, _, _, _ = tokenVestingNoStaking

    for vestingContract in [tv_staking, tv_noStaking]:
        assert vestingContract.getBeneficiary() == addrs.INVESTOR

        if st_sender != addrs.INVESTOR:
            with reverts(REV_MSG_NOT_BENEFICIARY):
                vestingContract.transferBeneficiary(st_sender, {"from": st_sender})

            tx = vestingContract.transferBeneficiary(
                st_sender, {"from": addrs.INVESTOR}
            )
            assert vestingContract.getBeneficiary() == st_sender
            assert tx.events["BeneficiaryTransferred"][0].values() == [
                addrs.INVESTOR,
                st_sender,
            ]


@given(st_sender=strategy("address"))
def test_transfer_beneficiary(addrs, cf, TokenVesting, st_sender):
    end = getChainTime() + QUARTER_YEAR + YEAR

    tv_staking = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        end,
        end,
        STAKABLE,
        BENEF_NON_TRANSF,
        cf.stateChainGateway,
    )

    tv_noStaking = addrs.DEPLOYER.deploy(
        TokenVesting,
        addrs.INVESTOR,
        addrs.REVOKER,
        getChainTime() + QUARTER_YEAR,
        getChainTime() + QUARTER_YEAR + YEAR,
        NON_STAKABLE,
        BENEF_NON_TRANSF,
        cf.stateChainGateway,
    )

    for vestingContract in [tv_staking, tv_noStaking]:
        assert vestingContract.getBeneficiary() == addrs.INVESTOR

        if st_sender != addrs.INVESTOR:
            with reverts(REV_MSG_NOT_BENEFICIARY):
                vestingContract.transferBeneficiary(st_sender, {"from": st_sender})

            with reverts(REV_MSG_BENEF_NOT_TRANSF):
                vestingContract.transferBeneficiary(st_sender, {"from": addrs.INVESTOR})
