from consts import *
from shared_tests import *
from brownie.test import given, strategy

from deploy import deploy_price_feeds
from brownie import (
    PriceFeedMock,
)

# When testing in local network only the derived default addresses are funded
@given(
    st_addresses=strategy("address[]"),
)
def test_addressChecker_balances(cf, st_addresses):
    addresses_balances = [
        web3.eth.get_balance(str(address)) for address in st_addresses
    ]
    assert cf.addressChecker.nativeBalances(st_addresses) == addresses_balances


def test_addressChecker_balances_gas(cf):
    # More than this returns a "Transaction ran out of gas" in testing. However, in a real network
    # we should be able to query more addresses.
    number_of_addresses = 25000
    list_of_addresses = [
        "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    ] * number_of_addresses
    balances = cf.addressChecker.nativeBalances(list_of_addresses)
    assert len(balances) == number_of_addresses
    assert all(
        balance == web3.eth.get_balance("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
        for balance in balances
    )


def test_addressChecker_deploymentStatus(cf, Deposit):

    deployedStatus = cf.addressChecker.contractsDeployed(
        [cf.flip, cf.vault, cf.keyManager, cf.addressChecker, cf.ALICE, cf.BOB]
    )
    assert deployedStatus == [True, True, True, True, False, False]

    depositAddr = getCreate2Addr(
        cf.vault.address,
        JUNK_HEX_PAD,
        Deposit,
        cleanHexStrPad(NATIVE_ADDR),
    )
    assert cf.addressChecker.contractsDeployed([depositAddr]) == [False]

    # Check that deploying a deposit contract in the depositAddr will change the deployed status
    signed_call_cf(cf, cf.vault.deployAndFetchBatch, [[JUNK_HEX_PAD, NATIVE_ADDR]])
    assert cf.addressChecker.contractsDeployed([depositAddr]) == [True]


@given(
    st_addresses=strategy("address[]"),
)
def test_addressChecker_balancesAndDeploymentStatus(cf, st_addresses):
    st_addresses.extend(
        [
            cf.flip.address,
            cf.vault.address,
            cf.keyManager.address,
            cf.addressChecker.address,
            cf.ALICE,
            cf.BOB,
        ]
    )

    results = []
    for address in st_addresses:
        results.append(
            (web3.eth.get_balance(str(address)), web3.eth.get_code(str(address)) != b"")
        )

    assert list(cf.addressChecker.addressStates(st_addresses)) == results


def test_addressChecker_balancesAndDeploymentStatus_gas(cf):
    # More than this returns a "Transaction ran out of gas" in testing. However, in a real network
    # we should be able to query more addresses.
    number_of_addresses = 11000
    list_of_addresses = [
        "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    ] * number_of_addresses
    balances = cf.addressChecker.addressStates(list_of_addresses)
    assert len(balances) == number_of_addresses


def test_addressChecker_price_feed_data(cf):
    deployed_feeds = deploy_price_feeds(
        cf.deployer, PriceFeedMock, ["BTC / USD", "ETH / USD", "SOL / USD"]
    )
    feed_addresses = [feed[1] for feed in deployed_feeds]

    result = cf.addressChecker.queryPriceFeeds(feed_addresses)
    assert len(result) == len(deployed_feeds)
    assert result == (
        (0, 0, 0, 0, 0, 8, "BTC / USD"),
        (0, 0, 0, 0, 0, 8, "ETH / USD"),
        (0, 0, 0, 0, 0, 8, "SOL / USD"),
    )

    btcPrice = 100000
    ethPrice = 2000
    solPrice = 150
    prices = [btcPrice, ethPrice, solPrice]
    descriptions = ["BTC / USD", "ETH / USD", "SOL / USD"]

    deployed_feeds = deploy_price_feeds(cf.deployer, PriceFeedMock, descriptions)
    feed_addresses = [feed[1] for feed in deployed_feeds]

    for feed, price in zip(deployed_feeds, prices):
        feed[1].updatePrice(price)

    result = cf.addressChecker.queryPriceFeeds(feed_addresses)
    assert len(result) == len(deployed_feeds)

    for i, (feed_data, price, desc) in enumerate(zip(result, prices, descriptions)):
        assert feed_data[0] > 0, f"Feed {i} answer is not positive"
        assert feed_data[1] == price, f"Feed {i} price mismatch"
        assert feed_data[2] > 0, f"Feed {i} startedAt is not positive"
        assert feed_data[3] > 0, f"Feed {i} updatedAt is not positive"
        assert feed_data[4] > 0, f"Feed {i} answeredInRound is not positive"
        assert feed_data[5] == 8, f"Feed {i} decimals is not 8"
        assert feed_data[6] == desc, f"Feed {i} description mismatch"
