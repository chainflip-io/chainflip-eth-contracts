from consts import *
from brownie import reverts
from utils import *
from shared_tests import *


def test_fetchDepositEth_transfer_fetchDepositToken_transfer(
    cf, token, DepositEth, DepositToken
):
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, JUNK_HEX_PAD, DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)

    assert cf.vault.balance() == 0

    signed_call_aggSigner(cf, cf.vault.fetchDepositEth, JUNK_HEX_PAD, sender=cf.ALICE)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert cf.vault.balance() == TEST_AMNT

    # Transfer the eth out the vault
    ethStartBalVault = cf.vault.balance()
    tokenStartBalRecipient = cf.BOB.balance()

    args = [[ETH_ADDR, cf.BOB, TEST_AMNT]]
    signed_call_aggSigner(cf, cf.vault.transfer, *args, sender=cf.ALICE)

    assert cf.vault.balance() - ethStartBalVault == -TEST_AMNT
    assert cf.BOB.balance() - tokenStartBalRecipient == TEST_AMNT

    balanceVault = cf.vault.balance()
    # Transferring out again should not transfer anything (vault empty) but it shouldn't fail
    signed_call_aggSigner(cf, cf.vault.transfer, *args)
    assert balanceVault == cf.vault.balance()

    # Fetch token deposit
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(
        cf.vault.address, JUNK_HEX_PAD, DepositToken, cleanHexStrPad(token.address)
    )
    token.transfer(depositAddr, TEST_AMNT, {"from": cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    args = [[JUNK_HEX_PAD, token]]
    signed_call_aggSigner(cf, cf.vault.fetchDepositToken, *args)

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == TEST_AMNT

    # Transfer half the tokens out the vault
    amount = TEST_AMNT / 2
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalRecipient = token.balanceOf(cf.ALICE)

    args = [[token, cf.BOB, amount]]
    signed_call_aggSigner(cf, cf.vault.transfer, *args)

    assert token.balanceOf(cf.vault) - tokenStartBalVault == -amount
    assert token.balanceOf(cf.BOB) - tokenStartBalRecipient == amount


def test_fetchDepositEthBatch_transfer_fetchDepositTokenBatch_transfer(
    cf, token, DepositEth, DepositToken
):
    swapIDs = [cleanHexStrPad(0), cleanHexStrPad(1)]
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)

    assert cf.vault.balance() == 0

    signed_call_aggSigner(cf, cf.vault.fetchDepositEthBatch, swapIDs, sender=cf.ALICE)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr2)) == 0
    assert cf.vault.balance() == 3 * TEST_AMNT

    # Transfer the eth out the vault
    ethStartBalVault = cf.vault.balance()
    ethStartBalRecipient = cf.ALICE.balance()

    args = [[ETH_ADDR, cf.ALICE, TEST_AMNT]]
    signed_call_aggSigner(cf, cf.vault.transfer, *args)

    assert cf.vault.balance() - ethStartBalVault == -TEST_AMNT
    assert cf.ALICE.balance() - ethStartBalRecipient == TEST_AMNT

    # Transferring out again should not transfer anything (vault empty) but it shouldn't fail
    balanceVault = cf.vault.balance()
    args = [[ETH_ADDR, cf.ALICE, (2 * TEST_AMNT) + 1]]
    signed_call_aggSigner(cf, cf.vault.transfer, *args)
    assert balanceVault == cf.vault.balance()

    # Fetch token deposit
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(
        cf.vault.address, swapIDs[0], DepositToken, cleanHexStrPad(token.address)
    )
    token.transfer(depositAddr, TEST_AMNT, {"from": cf.DEPLOYER})
    depositAddr2 = getCreate2Addr(
        cf.vault.address, swapIDs[1], DepositToken, cleanHexStrPad(token.address)
    )
    token.transfer(depositAddr2, 2 * TEST_AMNT, {"from": cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0
    fetchParamsArray = craftFetchParamsArray(swapIDs, [token, token])
    signed_call_aggSigner(
        cf, cf.vault.fetchDepositTokenBatch, fetchParamsArray, sender=cf.ALICE
    )

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == 3 * TEST_AMNT

    # Transfer half the tokens out the vault
    amount = TEST_AMNT * 1.5
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalRecipient = token.balanceOf(cf.ALICE)

    args = [[token, cf.ALICE, amount]]
    signed_call_aggSigner(cf, cf.vault.transfer, *args)

    assert token.balanceOf(cf.vault) - tokenStartBalVault == -amount
    assert token.balanceOf(cf.ALICE) - tokenStartBalRecipient == amount


def test_fetchDepositTokenBatch_transferBatch_fetchDepositEthBatch_transferBatch(
    cf, token, DepositEth, DepositToken
):
    swapIDs = [cleanHexStrPad(0), cleanHexStrPad(1)]
    # Fetch token deposit
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(
        cf.vault.address, swapIDs[0], DepositToken, cleanHexStrPad(token.address)
    )
    token.transfer(depositAddr, TEST_AMNT, {"from": cf.DEPLOYER})
    depositAddr2 = getCreate2Addr(
        cf.vault.address, swapIDs[1], DepositToken, cleanHexStrPad(token.address)
    )
    token.transfer(depositAddr2, 2 * TEST_AMNT, {"from": cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    fetchParamsArray = craftFetchParamsArray(swapIDs, [token, token])
    signed_call_aggSigner(
        cf, cf.vault.fetchDepositTokenBatch, fetchParamsArray, sender=cf.CHARLIE
    )

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == 3 * TEST_AMNT

    # Transfer most of the tokens out the vault
    amountAlice = TEST_AMNT * 1.5
    amountBob = int(TEST_AMNT * 0.5)
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalAlice = token.balanceOf(cf.ALICE)
    tokenStartBalBob = token.balanceOf(cf.BOB)

    transferParamsArray = craftTransferParamsArray(
        [token, token], [cf.ALICE, cf.BOB], [amountAlice, amountBob]
    )
    signed_call_aggSigner(
        cf, cf.vault.transferBatch, transferParamsArray, sender=cf.CHARLIE
    )

    assert token.balanceOf(cf.vault) - tokenStartBalVault == -amountAlice - amountBob
    assert token.balanceOf(cf.ALICE) - tokenStartBalAlice == amountAlice
    assert token.balanceOf(cf.BOB) - tokenStartBalBob == amountBob

    # Transferring out again should fail
    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        signed_call_aggSigner(
            cf, cf.vault.transferBatch, transferParamsArray, sender=cf.CHARLIE
        )

    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)

    assert cf.vault.balance() == 0

    signed_call_aggSigner(cf, cf.vault.fetchDepositEthBatch, swapIDs, sender=cf.CHARLIE)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr2)) == 0
    assert cf.vault.balance() == 3 * TEST_AMNT

    # Transfer the eth out the vault
    amountAlice = TEST_AMNT * 1.5
    amountBob = int(TEST_AMNT * 0.5)
    ethStartBalVault = cf.vault.balance()
    ethStartBalAlice = cf.ALICE.balance()
    ethStartBalBob = cf.BOB.balance()

    transferParamsArray = craftTransferParamsArray(
        [ETH_ADDR, ETH_ADDR],
        [cf.ALICE, cf.BOB],
        [amountAlice, amountBob],
    )
    signed_call_aggSigner(
        cf, cf.vault.transferBatch, transferParamsArray, sender=cf.CHARLIE
    )

    assert cf.vault.balance() == ethStartBalVault - amountAlice - amountBob
    assert cf.ALICE.balance() == ethStartBalAlice + amountAlice
    assert cf.BOB.balance() == ethStartBalBob + amountBob


def test_fetchDepositTokenBatch_transferBatch_allBatch(
    cf, token, DepositEth, DepositToken
):
    swapIDs = [cleanHexStrPad(0), cleanHexStrPad(1)]
    # Fetch token deposit
    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(
        cf.vault.address, swapIDs[0], DepositToken, cleanHexStrPad(token.address)
    )
    token.transfer(depositAddr, TEST_AMNT, {"from": cf.DEPLOYER})
    depositAddr2 = getCreate2Addr(
        cf.vault.address, swapIDs[1], DepositToken, cleanHexStrPad(token.address)
    )
    token.transfer(depositAddr2, 2 * TEST_AMNT, {"from": cf.DEPLOYER})

    assert token.balanceOf(cf.vault) == 0

    fetchParamsArray = craftFetchParamsArray(swapIDs, [token, token])
    signed_call_aggSigner(
        cf, cf.vault.fetchDepositTokenBatch, fetchParamsArray, sender=cf.CHARLIE
    )

    assert token.balanceOf(depositAddr) == 0
    assert token.balanceOf(cf.vault) == 3 * TEST_AMNT

    # Transfer most of the tokens out the vault
    amountAlice = TEST_AMNT * 1.5
    amountBob = int(TEST_AMNT * 0.5)
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalAlice = token.balanceOf(cf.ALICE)
    tokenStartBalBob = token.balanceOf(cf.BOB)

    transferParamsArray = craftTransferParamsArray(
        [token, token],
        [cf.ALICE, cf.BOB],
        [amountAlice, amountBob],
    )
    signed_call_aggSigner(
        cf, cf.vault.transferBatch, transferParamsArray, sender=cf.CHARLIE
    )

    assert token.balanceOf(cf.vault) - tokenStartBalVault == -amountAlice - amountBob
    assert token.balanceOf(cf.ALICE) - tokenStartBalAlice == amountAlice
    assert token.balanceOf(cf.BOB) - tokenStartBalBob == amountBob

    # Transferring out again should fail
    with reverts(REV_MSG_ERC20_EXCEED_BAL):
        transferParamsArray = craftTransferParamsArray(
            [token, token],
            [cf.ALICE, cf.BOB],
            [amountAlice, amountBob],
        )
        signed_call_aggSigner(cf, cf.vault.transferBatch, transferParamsArray)

    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(cf.vault.address, swapIDs[0], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr, TEST_AMNT)
    depositAddr2 = getCreate2Addr(cf.vault.address, swapIDs[1], DepositEth, "")
    cf.DEPLOYER.transfer(depositAddr2, 2 * TEST_AMNT)

    assert cf.vault.balance() == 0

    # Eth bals
    amountEthAlice = TEST_AMNT * 1.5
    amountEthBob = int(TEST_AMNT * 0.5)
    ethStartBalVault = cf.vault.balance()
    ethStartBalAlice = cf.ALICE.balance()
    ethStartBalBob = cf.BOB.balance()

    # Token bals
    amountTokenBob = int(TEST_AMNT * 0.25)
    tokenStartBalVault = token.balanceOf(cf.vault)
    tokenStartBalBob = token.balanceOf(cf.BOB)

    fetchParams = craftFetchParamsArray(swapIDs, [ETH_ADDR, ETH_ADDR])
    transferParams = craftTransferParamsArray(
        [ETH_ADDR, ETH_ADDR, token],
        [cf.ALICE, cf.BOB, cf.BOB],
        [amountEthAlice, amountEthBob, amountTokenBob],
    )
    args = (fetchParams, transferParams)

    signed_call_aggSigner(cf, cf.vault.allBatch, *args, sender=cf.CHARLIE)

    # Eth bals
    assert (
        cf.vault.balance()
        == ethStartBalVault + (3 * TEST_AMNT) - amountEthAlice - amountEthBob
    )
    assert cf.ALICE.balance() == ethStartBalAlice + amountEthAlice
    assert cf.BOB.balance() == ethStartBalBob + amountEthBob

    # Token bals
    assert token.balanceOf(cf.vault) == tokenStartBalVault - amountTokenBob
    assert token.balanceOf(cf.BOB) == tokenStartBalBob + amountTokenBob
