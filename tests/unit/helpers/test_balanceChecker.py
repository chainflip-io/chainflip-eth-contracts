from consts import *
from shared_tests import *
from brownie.test import given, strategy


# When testing in local network only the derived default addresses are funded
@given(
    st_addresses=strategy("address[]"),
)
def test_balanceChecker(cf, st_addresses):
    addresses_balances = [
        web3.eth.get_balance(str(address)) for address in st_addresses
    ]
    assert cf.balanceChecker.getNativeBalances(st_addresses) == addresses_balances


def test_balanceChecker_gas(cf):
    # More than this returns a "Transaction ran out of gas" in testing. However, in a real network
    # we should be able to query more addresses.
    number_of_addresses = 27000
    list_of_addresses = [
        "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    ] * number_of_addresses
    balances = cf.balanceChecker.getNativeBalances(list_of_addresses)
    assert len(balances) == number_of_addresses
    assert all(
        balance == web3.eth.get_balance("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
        for balance in balances
    )


## TODO: Add test for getDeployedStatus and getNativeBalancesAndDeployedStatus
