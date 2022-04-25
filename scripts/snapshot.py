import sys
import os
import json
import csv

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import (
    chain,
    accounts,
    KeyManager,
    Vault,
    StakeManager,
    FLIP,
    history,
    web3,
)
from deploy import deploy_set_Chainflip_contracts
from web3._utils.abi import get_constructor_abi, merge_args_and_kwargs
from web3._utils.events import get_event_data
from web3._utils.filters import construct_event_filter_params
from web3._utils.contracts import encode_abi

# So brownie can run a snapshot separately from airdrop
def main():
    rinkeby_flip_deployed = "0xbFf4044285738049949512Bd46B42056Ce5dD59b"
    # Using latest block for now as snapshot block
    snapshot(web3.eth.block_number, rinkeby_flip_deployed)


def snapshot(
    snapshot_blocknumber=web3.eth.block_number,
    rinkeby_flip_deployed="0xbFf4044285738049949512Bd46B42056Ce5dD59b",
    filename="snapshot.csv",
):

    # Not the ABI of the current FLIP contract in soundcheck but we only need the generic ERC20 interfaces
    with open("build/contracts/FLIP.json") as f:
        info_json = json.load(f)
    abi = info_json["abi"]

    flipContract = web3.eth.contract(address=rinkeby_flip_deployed, abi=abi)

    # It will throw an error if there are more than 10.000 events (Infura Limitation)
    # Split it if that is the case - there is no time requirement anyway
    events = list(
        fetch_events(
            flipContract.events.Transfer, from_block=0, to_block=snapshot_blocknumber
        )
    )

    receiver_list = []
    print("Got", len(events), "events")

    # Get list of unique addresses that have recieved FLIP
    for event in events:
        toAddress = event.args.to
        if toAddress not in receiver_list:
            receiver_list.append(toAddress)
    holder_balances = []
    totalBalance = 0

    # Get balances of receivers and check if they are holders
    holder_list = []
    for holder in receiver_list:
        holderBalance = flipContract.functions.balanceOf(holder).call()
        # HolderBalance>0 already filters out the zero address (when tokens are burnt)
        if holderBalance > 0:
            totalBalance += holderBalance
            holder_balances.append(holderBalance)
            holder_list.append(holder)

    # Health check
    assert len(holder_list) == len(holder_balances)
    totalSupply = flipContract.functions.totalSupply().call()
    assert totalSupply == totalBalance

    # Can be checked in Etherscan that the values match
    print(totalSupply)
    print(len(holder_list))

    # Add checksum for security purposes
    holder_list.append("NumberHolders:" + str(len(holder_list)))
    holder_balances.append(totalBalance)
    rows = zip(holder_list, holder_balances)

    with open(filename, "w") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)

    return filename


def fetch_events(
    event,
    argument_filters=None,
    from_block=None,
    to_block="latest",
    address=None,
    topics=None,
):
    """Get events using eth_getLogs API.

    This is a stateless method, as opposite to createFilter and works with
    stateless nodes like QuikNode and Infura.

    :param event: Event instance from your contract.events
    :param argument_filters:
    :param from_block: Start block. Use 0 for all history/
    :param to_block: Fetch events until this contract
    :param address:
    :param topics:
    :return:
    """

    if from_block is None:
        raise TypeError("Missing mandatory keyword argument to getLogs: from_Block")

    abi = event._get_event_abi()
    abi_codec = event.web3.codec

    # Set up any indexed event filters if needed
    argument_filters = dict()
    _filters = dict(**argument_filters)

    data_filter_set, event_filter_params = construct_event_filter_params(
        abi,
        abi_codec,
        contract_address=event.address,
        argument_filters=_filters,
        fromBlock=from_block,
        toBlock=to_block,
        address=address,
        topics=topics,
    )

    # Call node over JSON-RPC API
    logs = event.web3.eth.get_logs(event_filter_params)

    # Convert raw binary event data to easily manipulable Python objects
    for entry in logs:
        data = get_event_data(abi_codec, abi, entry)
        yield data
