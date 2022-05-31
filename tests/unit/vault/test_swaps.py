from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *
from shared_tests import *


# Tests enable and disable swaps


@given(
    st_sender=strategy("address"),
)
def test_enableSwaps_rev_gov(cf, st_sender):
    assert cf.vault.getSwapsEnabled() == False
    if st_sender == cf.gov:
        cf.vault.enableSwaps({"from": st_sender})
        assert cf.vault.getSwapsEnabled() == True
    else:
        with reverts(REV_MSG_GOV_GOVERNOR):
            cf.vault.enableSwaps({"from": st_sender})
            assert cf.vault.getSwapsEnabled() == False


def test_enableSwaps_rev_enabled(cf):
    cf.vault.enableSwaps({"from": cf.gov})

    with reverts(REV_MSG_VAULT_SWAPS_EN):
        cf.vault.enableSwaps({"from": cf.gov})


@given(
    st_sender=strategy("address"),
)
def test_disableSwaps_rev_gov(cf, st_sender):
    assert cf.vault.getSwapsEnabled() == False
    cf.vault.enableSwaps({"from": cf.gov})
    assert cf.vault.getSwapsEnabled() == True
    if st_sender == cf.gov:
        cf.vault.disableSwaps({"from": st_sender})
        assert cf.vault.getSwapsEnabled() == False
    else:
        with reverts(REV_MSG_GOV_GOVERNOR):
            cf.vault.disableSwaps({"from": st_sender})
            assert cf.vault.getSwapsEnabled() == True


def test_enableSwaps_rev_disabled(cf):
    with reverts(REV_MSG_VAULT_SWAPS_DIS):
        cf.vault.disableSwaps({"from": cf.gov})


# SwapETH


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32", exclude=(0).to_bytes(32, "big")),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_swapETH(cf, st_sender, st_egressParams, st_egressReceiver, st_amount):
    cf.vault.enableSwaps({"from": cf.gov})
    tx = cf.vault.swapETH(
        st_egressParams, st_egressReceiver, {"from": st_sender, "amount": st_amount}
    )

    assert tx.events["SwapETH"]["amount"] == st_amount
    assert tx.events["SwapETH"]["egressParams"] == st_egressParams
    assert tx.events["SwapETH"]["egressReceiver"] == "0x" + cleanHexStr(
        st_egressReceiver
    )


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32"),
)
def test_swapETH_rev_suspended(cf, st_sender, st_egressParams, st_egressReceiver):
    cf.vault.suspend({"from": cf.gov})
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.swapETH(st_egressParams, st_egressReceiver, {"from": st_sender})


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32"),
)
def test_swapETH_rev_disabled(cf, st_sender, st_egressParams, st_egressReceiver):
    with reverts(REV_MSG_VAULT_SWAPS_DIS):
        cf.vault.swapETH(st_egressParams, st_egressReceiver, {"from": st_sender})


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32"),
)
def test_swapETH_rev_nzuint(cf, st_sender, st_egressParams, st_egressReceiver):
    cf.vault.enableSwaps({"from": cf.gov})
    with reverts(REV_MSG_NZ_UINT):
        cf.vault.swapETH(st_egressParams, st_egressReceiver, {"from": st_sender})


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_swapETH_rev_nzbytes(cf, st_sender, st_egressParams, st_amount):
    cf.vault.enableSwaps({"from": cf.gov})
    with reverts(REV_MSG_NZ_BYTES32):
        cf.vault.swapETH(st_egressParams, 0, {"from": st_sender, "amount": st_amount})


# SwapToken


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32", exclude=(0).to_bytes(32, "big")),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_swapToken(cf, token, st_sender, st_egressParams, st_egressReceiver, st_amount):
    cf.vault.enableSwaps({"from": cf.gov})
    token.transfer(st_sender, st_amount)
    token.approve(cf.vault, st_amount, {"from": st_sender})
    tx = cf.vault.swapToken(
        st_egressParams, st_egressReceiver, token, st_amount, {"from": st_sender}
    )

    assert tx.events["SwapToken"]["amount"] == st_amount
    assert tx.events["SwapToken"]["egressParams"] == st_egressParams
    assert tx.events["SwapToken"]["egressReceiver"] == "0x" + cleanHexStr(
        st_egressReceiver
    )
    assert tx.events["SwapToken"]["ingressToken"] == token.address


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32", exclude=(0).to_bytes(32, "big")),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_swapToken_rev_bal(
    cf, token, st_sender, st_egressParams, st_egressReceiver, st_amount
):
    cf.vault.enableSwaps({"from": cf.gov})
    if st_sender != cf.DEPLOYER:
        with reverts(REV_MSG_ERC20_EXCEED_BAL):
            cf.vault.swapToken(
                st_egressParams,
                st_egressReceiver,
                token,
                st_amount,
                {"from": st_sender},
            )


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32"),
    st_amount=strategy("uint"),
)
def test_swapToken_rev_suspended(
    cf, token, st_sender, st_egressParams, st_egressReceiver, st_amount
):
    cf.vault.suspend({"from": cf.gov})
    with reverts(REV_MSG_GOV_SUSPENDED):
        cf.vault.swapToken(
            st_egressParams, st_egressReceiver, token, st_amount, {"from": st_sender}
        )


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32"),
    st_amount=strategy("uint"),
)
def test_swapToken_rev_disabled(
    cf, token, st_sender, st_egressParams, st_egressReceiver, st_amount
):
    with reverts(REV_MSG_VAULT_SWAPS_DIS):
        cf.vault.swapToken(
            st_egressParams, st_egressReceiver, token, st_amount, {"from": st_sender}
        )


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32"),
)
def test_swapToken_rev_nzuint(cf, token, st_sender, st_egressParams, st_egressReceiver):
    cf.vault.enableSwaps({"from": cf.gov})
    with reverts(REV_MSG_NZ_UINT):
        cf.vault.swapToken(
            st_egressParams, st_egressReceiver, token, 0, {"from": st_sender}
        )


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_swapToken_rev_nzbytes(
    cf, token, st_sender, st_egressParams, st_egressReceiver, st_amount
):
    cf.vault.enableSwaps({"from": cf.gov})
    token.transfer(st_sender, st_amount)
    with reverts(REV_MSG_NZ_BYTES32):
        cf.vault.swapToken(st_egressParams, 0, token, st_amount, {"from": st_sender})


@given(
    st_sender=strategy("address"),
    st_egressParams=strategy("string"),
    st_egressReceiver=strategy("bytes32"),
    st_amount=strategy("uint", exclude=0, max_value=TEST_AMNT),
)
def test_swapToken_rev_nzaddrs(
    cf, st_sender, st_egressParams, st_amount, st_egressReceiver
):
    cf.vault.enableSwaps({"from": cf.gov})
    with reverts(REV_MSG_NZ_ADDR):
        cf.vault.swapToken(
            st_egressParams,
            st_egressReceiver,
            ZERO_ADDR,
            st_amount,
            {"from": st_sender},
        )
