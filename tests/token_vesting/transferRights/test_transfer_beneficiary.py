from consts import *
from brownie import reverts
from brownie.test import given, strategy
from shared_tests_tokenVesting import *


@given(st_sender=strategy("address"))
def test_transfer_beneficiary_0(
    addrs, tokenVestingStaking, tokenVestingNoStaking, st_sender
):
    tv_staking, _, _, _ = tokenVestingStaking
    tv_noStaking, _, _, _ = tokenVestingNoStaking

    for vestingContract in [tv_staking, tv_noStaking]:
        assert vestingContract.getBeneficiary() == addrs.BENEFICIARY

        if st_sender != addrs.BENEFICIARY:
            with reverts(REV_MSG_NOT_BENEFICIARY):
                vestingContract.transferBeneficiary(st_sender, {"from": st_sender})

            tx = vestingContract.transferBeneficiary(
                st_sender, {"from": addrs.BENEFICIARY}
            )
            assert vestingContract.getBeneficiary() == st_sender
            assert tx.events["BeneficiaryTransferred"][0].values() == [
                addrs.BENEFICIARY,
                st_sender,
            ]


@given(st_sender=strategy("address"))
def test_transfer_beneficiary_1(
    addrs, cf, TokenVestingNoStaking, TokenVestingStaking, st_sender
):
    end = getChainTime() + QUARTER_YEAR + YEAR

    tv_staking = addrs.DEPLOYER.deploy(
        TokenVestingStaking,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        getChainTime() + QUARTER_YEAR,
        end,
        BENEF_NON_TRANSF,
        cf.stateChainGateway,
        cf.flip,
    )

    tv_noStaking = addrs.DEPLOYER.deploy(
        TokenVestingNoStaking,
        addrs.BENEFICIARY,
        addrs.REVOKER,
        getChainTime() + QUARTER_YEAR,
        getChainTime() + QUARTER_YEAR + YEAR,
        BENEF_NON_TRANSF,
    )

    for vestingContract in [tv_staking, tv_noStaking]:
        assert vestingContract.getBeneficiary() == addrs.BENEFICIARY

        if st_sender != addrs.BENEFICIARY:
            with reverts(REV_MSG_NOT_BENEFICIARY):
                vestingContract.transferBeneficiary(st_sender, {"from": st_sender})

            with reverts(REV_MSG_BENEF_NOT_TRANSF):
                vestingContract.transferBeneficiary(
                    st_sender, {"from": addrs.BENEFICIARY}
                )
