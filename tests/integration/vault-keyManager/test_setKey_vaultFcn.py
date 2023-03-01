from consts import *
from shared_tests import *
from brownie import reverts
from brownie.test import given, strategy
from utils import *
from random import choices


@given(
    st_fetchAmounts=strategy(
        "uint[]", max_value=TEST_AMNT, max_length=int(INIT_TOKEN_SUPPLY / TEST_AMNT)
    ),
    st_fetchSwapIDs=strategy("bytes32[]", unique=True),
    st_tranRecipients=strategy("address[]", unique=True),
    st_tranAmounts=strategy("uint[]", max_value=TEST_AMNT),
    st_sender=strategy("address"),
)
def test_setAggKeyWithAggKey_allBatch(
    cfAW,
    token,
    token2,
    Deposit,
    st_fetchAmounts,
    st_fetchSwapIDs,
    st_tranRecipients,
    st_tranAmounts,
    st_sender,
):

    # Allowing this breaks the refund test
    if st_sender in st_tranRecipients:
        return

    # Change agg keys
    setAggKeyWithAggKey_test(cfAW)

    # Sort out deposits first so enough can be sent to the create2 addresses
    fetchMinLen = trimToShortest([st_fetchAmounts, st_fetchSwapIDs])
    tokensList = [NATIVE_ADDR, token, token2]
    fetchTokens = choices(tokensList, k=fetchMinLen)

    fetchTotals = {
        tok: sum([st_fetchAmounts[i] for i, x in enumerate(fetchTokens) if x == tok])
        for tok in tokensList
    }

    # Transfer tokens to the deposit addresses
    for am, id, tok in zip(st_fetchAmounts, st_fetchSwapIDs, fetchTokens):
        # Get the address to deposit to and deposit
        if tok == NATIVE_ADDR:
            depositAddr = getCreate2Addr(
                cfAW.vault.address, id.hex(), Deposit, cleanHexStrPad(NATIVE_ADDR)
            )
            cfAW.SAFEKEEPER.transfer(depositAddr, am)
        else:
            depositAddr = getCreate2Addr(
                cfAW.vault.address, id.hex(), Deposit, cleanHexStrPad(tok.address)
            )
            tok.transfer(depositAddr, am, {"from": cfAW.SAFEKEEPER})

    assert cfAW.vault.balance() == 0
    assert token.balanceOf(cfAW.vault) == 0
    assert token2.balanceOf(cfAW.vault) == 0

    # Transfers
    tranMinLen = trimToShortest([st_tranRecipients, st_tranAmounts])
    tranTokens = choices(tokensList, k=tranMinLen)

    tranTotals = {
        tok: sum([st_tranAmounts[i] for i, x in enumerate(tranTokens) if x == tok])
        for tok in tokensList
    }
    validEthIdxs = getValidTranIdxs(
        tranTokens, st_tranAmounts, fetchTotals[NATIVE_ADDR], NATIVE_ADDR
    )
    tranTotals[NATIVE_ADDR] = sum(
        [
            st_tranAmounts[i]
            for i, x in enumerate(tranTokens)
            if x == NATIVE_ADDR and i in validEthIdxs
        ]
    )

    nativeStartBalVault = cfAW.vault.balance()
    nativeBals = [web3.eth.get_balance(str(recip)) for recip in st_tranRecipients]
    tokenBals = [token.balanceOf(recip) for recip in st_tranRecipients]
    token2Bals = [token2.balanceOf(recip) for recip in st_tranRecipients]

    deployFetchParams = craftDeployFetchParamsArray(st_fetchSwapIDs, fetchTokens)
    transferParams = craftTransferParamsArray(
        tranTokens, st_tranRecipients, st_tranAmounts
    )
    args = (deployFetchParams, [], transferParams)

    # Check allBatch fails with the old agg key
    with reverts(REV_MSG_SIG):
        signed_call_cf(cfAW, cfAW.vault.allBatch, *args, sender=st_sender)

    # If it tries to transfer an amount of tokens out the vault that is more than it fetched, it'll fail gracefully
    if any([tranTotals[tok] > fetchTotals[tok] for tok in tokensList[1:]]):
        tx = signed_call_cf(
            cfAW, cfAW.vault.allBatch, *args, sender=st_sender, signer=AGG_SIGNER_2
        )
        # There might be multiple failures, so just check that there is at least one
        assert len(tx.events["TransferTokenFailed"]) >= 1
    else:
        signed_call_cf(
            cfAW, cfAW.vault.allBatch, *args, sender=st_sender, signer=AGG_SIGNER_2
        )

        assert cfAW.vault.balance() == nativeStartBalVault + (
            fetchTotals[NATIVE_ADDR] - tranTotals[NATIVE_ADDR]
        )
        assert token.balanceOf(cfAW.vault) == fetchTotals[token] - tranTotals[token]
        assert token2.balanceOf(cfAW.vault) == fetchTotals[token2] - tranTotals[token2]

        for i in range(len(st_tranRecipients)):
            if tranTokens[i] == NATIVE_ADDR:
                if i in validEthIdxs:
                    assert (
                        web3.eth.get_balance(str(st_tranRecipients[i]))
                        == nativeBals[i] + st_tranAmounts[i]
                    )
            elif tranTokens[i] == token:
                assert (
                    token.balanceOf(st_tranRecipients[i])
                    == tokenBals[i] + st_tranAmounts[i]
                )
            elif tranTokens[i] == token2:
                assert (
                    token2.balanceOf(st_tranRecipients[i])
                    == token2Bals[i] + st_tranAmounts[i]
                )
            else:
                assert False, "Panic"


# Check that updating the Governor Key in the KeyManager takes effect
def test_setGovKeyWithAggKey_govWithdrawal(cf):
    # Check that it passes the isGovernor check initially
    with reverts(REV_MSG_GOV_ENABLED_GUARD):
        cf.vault.govWithdraw([NATIVE_ADDR], {"from": cf.GOVERNOR})

    setGovKeyWithAggKey_test(cf)

    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.vault.govWithdraw([NATIVE_ADDR], {"from": cf.GOVERNOR})


def test_setGovKeyWithGovKey_govWithdrawal(cf):
    # Check that it passes the isGovernor check initially
    with reverts(REV_MSG_GOV_ENABLED_GUARD):
        cf.vault.govWithdraw([NATIVE_ADDR], {"from": cf.GOVERNOR})

    setGovKeyWithGovKey_test(cf)

    with reverts(REV_MSG_GOV_GOVERNOR):
        cf.vault.govWithdraw([NATIVE_ADDR], {"from": cf.GOVERNOR})


# Check that updating the Community Key in the KeyManager takes effect
def test_setCommKeyWithAggKey_govWithdrawal(cf):
    # Check that the community Guard is enabled
    with reverts(REV_MSG_GOV_ENABLED_GUARD):
        cf.vault.govWithdraw([NATIVE_ADDR], {"from": cf.GOVERNOR})

    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
        cf.vault.disableCommunityGuard({"from": cf.COMMUNITY_KEY_2})

    setCommKeyWithAggKey_test(cf)

    cf.vault.disableCommunityGuard({"from": cf.COMMUNITY_KEY_2})

    # Check that it now passes the community Guard
    with reverts(REV_MSG_GOV_NOT_SUSPENDED):
        cf.vault.govWithdraw([NATIVE_ADDR], {"from": cf.GOVERNOR})


# Check that updating the Community Key in the KeyManager takes effect
def test_setCommKeyWithCommKey_govWithdrawal(cf):
    # Check that the community Guard is enabled
    with reverts(REV_MSG_GOV_ENABLED_GUARD):
        cf.vault.govWithdraw([NATIVE_ADDR], {"from": cf.GOVERNOR})

    with reverts(REV_MSG_GOV_NOT_COMMUNITY):
        cf.vault.disableCommunityGuard({"from": cf.COMMUNITY_KEY_2})

    setCommKeyWithCommKey_test(cf)

    cf.vault.disableCommunityGuard({"from": cf.COMMUNITY_KEY_2})

    # Check that it now passes the community Guard
    with reverts(REV_MSG_GOV_NOT_SUSPENDED):
        cf.vault.govWithdraw([NATIVE_ADDR], {"from": cf.GOVERNOR})
