from consts import *
from shared_tests import *
from eth_abi import encode_abi
from brownie.test import given, strategy


def check_gas_test(tx, gas_to_use):
    assert "GasTest" in tx.events
    assert tx.events["GasTest"]["gasUsed"] > gas_to_use
    assert tx.gas_used > gas_to_use
    assert tx.gas_used > tx.events["GasTest"]["gasUsed"]

    print("gas_to_use", gas_to_use)
    print("gasUsed", tx.events["GasTest"]["gasUsed"])


def test_cfTest_defaultGas(
    cf,
    cfTester,
):
    default_gas_used = 6.5 * 10**6

    message = encode_abi(["string", "uint256"], [cfTester.GAS_TEST(), 0])

    cf.ALICE.transfer(cf.vault.address, TEST_AMNT * 10)
    tx = cfTester.cfReceive(0, 0, message, NON_ZERO_ADDR, 0, {"from": cf.vault})
    assert "ReceivedxSwapAndCall" in tx.events
    check_gas_test(tx, default_gas_used)

    tx = cfTester.cfReceivexCall(0, 0, message, {"from": cf.vault})
    assert "ReceivedxCall" in tx.events
    check_gas_test(tx, default_gas_used)


@given(
    st_gas_to_use=strategy("uint256", min_value=50 * 10**3, max_value=15 * 10**6),
)
def test_cfTest_gas(cf, cfTester, st_gas_to_use):
    message = encode_abi(["string", "uint256"], [cfTester.GAS_TEST(), st_gas_to_use])

    cf.ALICE.transfer(cf.vault.address, TEST_AMNT * 10)
    tx = cfTester.cfReceive(0, 0, message, NON_ZERO_ADDR, 0, {"from": cf.vault})
    assert "ReceivedxSwapAndCall" in tx.events
    check_gas_test(tx, st_gas_to_use)

    tx = cfTester.cfReceivexCall(0, 0, message, {"from": cf.vault})
    assert "ReceivedxCall" in tx.events
    check_gas_test(tx, st_gas_to_use)


@given(
    st_message=strategy("bytes"),
)
def test_cfTest_noGasTest(cf, cfTester, st_message):
    cf.ALICE.transfer(cf.vault.address, TEST_AMNT * 10)
    tx = cfTester.cfReceive(0, 0, st_message, NON_ZERO_ADDR, 0, {"from": cf.vault})
    assert "ReceivedxSwapAndCall" in tx.events
    assert "GasTest" not in tx.events

    tx = cfTester.cfReceivexCall(0, 0, st_message, {"from": cf.vault})
    assert "ReceivedxCall" in tx.events
    assert "GasTest" not in tx.events


def test_transfer_eth(cf, cfTester, Deposit):
    assert web3.eth.get_balance(NON_ZERO_ADDR) == 0
    cfTester.transferEth(NON_ZERO_ADDR, {"from": cf.ALICE, "value": TEST_AMNT})
    assert web3.eth.get_balance(NON_ZERO_ADDR) == TEST_AMNT

    # Transfer to a deployed Deposit contract
    depositAddr = getCreate2Addr(
        cf.vault.address, JUNK_HEX_PAD, Deposit, cleanHexStrPad(NATIVE_ADDR)
    )
    signed_call_cf(
        cf, cf.vault.deployAndFetchBatch, [[JUNK_HEX_PAD, NATIVE_ADDR]], sender=cf.ALICE
    )

    assert web3.eth.get_balance(depositAddr) == 0
    cfTester.transferEth(depositAddr, {"from": cf.ALICE, "value": TEST_AMNT})
    assert web3.eth.get_balance(depositAddr) == 0
    assert web3.eth.get_balance(cf.vault.address) == TEST_AMNT


def test_transfer_token(cf, cfTester, Deposit):
    assert cf.flip.balanceOf(NON_ZERO_ADDR) == 0
    cf.flip.approve(cfTester, TEST_AMNT, {"from": cf.ALICE})
    cfTester.transferToken(
        NON_ZERO_ADDR, cf.flip.address, TEST_AMNT, {"from": cf.ALICE}
    )
    assert cf.flip.balanceOf(NON_ZERO_ADDR) == TEST_AMNT

    # Transfer to a deployed Deposit contract
    depositAddr = getCreate2Addr(
        cf.vault.address, JUNK_HEX_PAD, Deposit, cleanHexStrPad(cf.flip.address)
    )
    signed_call_cf(
        cf,
        cf.vault.deployAndFetchBatch,
        [[JUNK_HEX_PAD, cf.flip.address]],
        sender=cf.ALICE,
    )

    assert cf.flip.balanceOf(depositAddr) == 0
    cf.flip.approve(cfTester, TEST_AMNT, {"from": cf.ALICE})
    cfTester.transferToken(depositAddr, cf.flip.address, TEST_AMNT, {"from": cf.ALICE})
    assert cf.flip.balanceOf(depositAddr) == TEST_AMNT


def test_multipleContractSwap_token(cf, cfTester):
    numberOfSwaps = 2
    cf.flip.approve(cfTester, TEST_AMNT * numberOfSwaps, {"from": cf.ALICE})
    tx = cfTester.multipleContractSwap(
        1,
        JUNK_HEX_PAD,
        2,
        cf.flip.address,
        TEST_AMNT,
        JUNK_HEX_PAD,
        numberOfSwaps,
        {"from": cf.ALICE},
    )
    assert len(tx.events["SwapToken"]) == numberOfSwaps
    assert cf.flip.balanceOf(cfTester) == 0
    assert cf.flip.balanceOf(cf.vault) == TEST_AMNT * numberOfSwaps


def test_multipleContractSwap_native(cf, cfTester):
    numberOfSwaps = 2
    tx = cfTester.multipleContractSwap(
        1,
        JUNK_HEX_PAD,
        2,
        NATIVE_ADDR,
        TEST_AMNT,
        JUNK_HEX_PAD,
        numberOfSwaps,
        {"from": cf.ALICE, "value": TEST_AMNT * numberOfSwaps},
    )
    assert len(tx.events["SwapNative"]) == numberOfSwaps
    assert web3.eth.get_balance(cfTester.address) == 0
    assert web3.eth.get_balance(cf.vault.address) == TEST_AMNT * numberOfSwaps


def test_multipleContractCall_token(cf, cfTester):
    numberOfSwaps = 2
    cf.flip.approve(cfTester, TEST_AMNT * numberOfSwaps, {"from": cf.ALICE})
    tx = cfTester.multipleContractCall(
        1,
        JUNK_HEX_PAD,
        2,
        JUNK_HEX_PAD,
        JUNK_INT,
        cf.flip.address,
        TEST_AMNT,
        JUNK_HEX_PAD,
        numberOfSwaps,
        {"from": cf.ALICE},
    )
    assert len(tx.events["XCallToken"]) == numberOfSwaps
    assert cf.flip.balanceOf(cfTester) == 0
    assert cf.flip.balanceOf(cf.vault) == TEST_AMNT * numberOfSwaps


def test_multipleContractCall_native(cf, cfTester):
    numberOfSwaps = 2
    tx = cfTester.multipleContractCall(
        1,
        JUNK_HEX_PAD,
        2,
        JUNK_HEX_PAD,
        JUNK_INT,
        NATIVE_ADDR,
        TEST_AMNT,
        JUNK_HEX_PAD,
        numberOfSwaps,
        {"from": cf.ALICE, "value": TEST_AMNT * numberOfSwaps},
    )
    assert len(tx.events["XCallNative"]) == numberOfSwaps
    assert web3.eth.get_balance(cfTester.address) == 0
    assert web3.eth.get_balance(cf.vault.address) == TEST_AMNT * numberOfSwaps
