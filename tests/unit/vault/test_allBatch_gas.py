import pytest
from consts import *
from utils import *
from shared_tests import *


@pytest.fixture(autouse=True)
def isolation():
    pass


# Transferring one more to prevent the gas difference of the balance reduced to zero


def test_allBatch_transfer_native(cf_minimal):
    cf_minimal.SAFEKEEPER.transfer(cf_minimal.vault.address, TEST_AMNT + 1)
    signed_call_cf(
        cf_minimal,
        cf_minimal.vault.allBatch,
        [],
        [],
        [[NATIVE_ADDR, cf_minimal.ALICE, TEST_AMNT]],
    )


def test_allBatch_transfer_token(cf_minimal, token_minimal):
    token_minimal.transfer(
        cf_minimal.vault.address, TEST_AMNT + 1, {"from": cf_minimal.SAFEKEEPER}
    )
    signed_call_cf(
        cf_minimal,
        cf_minimal.vault.allBatch,
        [],
        [],
        [[token_minimal.address, cf_minimal.ALICE, TEST_AMNT]],
    )


def test_allBatch_deploy_fetch(cf_minimal, token_minimal, Deposit):
    native_swap_id = cleanHexStrPad(web3.toHex(1))
    native_deposit_addr = getCreate2Addr(
        cf_minimal.vault.address, native_swap_id, Deposit, cleanHexStrPad(NATIVE_ADDR)
    )
    cf_minimal.SAFEKEEPER.transfer(native_deposit_addr, TEST_AMNT)
    signed_call_cf(
        cf_minimal,
        cf_minimal.vault.allBatch,
        [[native_swap_id, NATIVE_ADDR]],
        [],
        [],
    )

    token_swap_id = cleanHexStrPad(web3.toHex(2))
    token_deposit_addr = getCreate2Addr(
        cf_minimal.vault.address,
        token_swap_id,
        Deposit,
        cleanHexStrPad(token_minimal.address),
    )
    token_minimal.transfer(
        token_deposit_addr, TEST_AMNT, {"from": cf_minimal.SAFEKEEPER}
    )
    signed_call_cf(
        cf_minimal,
        cf_minimal.vault.allBatch,
        [[token_swap_id, token_minimal.address]],
        [],
        [],
    )


def test_allBatch_deploy_native(cf_minimal, token_minimal, Deposit):
    token_swap_id = cleanHexStrPad(web3.toHex(2))
    token_deposit_addr = getCreate2Addr(
        cf_minimal.vault.address,
        token_swap_id,
        Deposit,
        cleanHexStrPad(token_minimal.address),
    )
    token_minimal.transfer(
        token_deposit_addr, TEST_AMNT, {"from": cf_minimal.SAFEKEEPER}
    )
    signed_call_cf(
        cf_minimal,
        cf_minimal.vault.allBatch,
        [],
        [[token_deposit_addr, token_minimal.address]],
        [],
    )
