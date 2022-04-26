import sys
import os
import json
import csv
import logging
import time
import os.path

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

# from .airdrop import airdrop


# This will continue logging at the end of the previous log (running .INFO for development purposes)
logname = "airdrop.log"

logging.basicConfig(filename=logname, level=logging.INFO)
# In the end probably do this to log also all RPC calls
# logging.basicConfig(filename='airdrop.log', level=logging.DEBUG)
# So brownie can run a snapshot separately from airdrop

rinkeby_flip_deployed = "0xbFf4044285738049949512Bd46B42056Ce5dD59b"
rinkeby_sm_deployed = "0x3A96a2D552356E17F97e98FF55f69fDFb3545892"
oldFlipSnapshotFilename = "snapshot_old_flip.csv"
newFlipSnapshotFilename = "snapshot_new_flip.csv"
oldFlipDeployer = "0x4D1951e64D3D02A3CBa0D0ef5438f732850ED592"


def main():
    parsedLog = []
    # Start parsing log
    file = open(logname, "r")
    for line in file.readlines():
        # Only check info messages from previous run (disregard DEBUG and ERROR) and remove end of line
        infoMessage = line.rstrip("\n").split("INFO:root:")
        if len(infoMessage) > 1:
            parsedLog.append(infoMessage[1])

    logging.info(
        "=========================   Running snapshot and airdrop script  =========================="
    )

    # try:
    #     assert chain.id == 4, "Wrong chain"
    # except AssertionError:
    #     logging.error ("Wrong chain")
    #     raise

    if (not "Snapshot completed in " + oldFlipSnapshotFilename in parsedLog) or (
        not os.path.exists(oldFlipSnapshotFilename)
    ):
        assert chain.id == 4, logging.error("Wrong chain. Should be running in Rinkeby")
        logging.info("Old FLIP snapshot not taken previously")
        # Using latest block for now as snapshot block
        snapshot(web3.eth.block_number, rinkeby_flip_deployed, oldFlipSnapshotFilename)
    else:
        logging.info("Skipped old FLIP snapshot - snapshop already taken")

    assert chain.id > 10, logging.error(
        "Wrong chain. Should be running in local hardhat tesnet"
    )

    # Skip airdrop if it is logged as succesfully. However, when failed we should check transaction by transaction in case brownie has emited the transaction but not received the receipt back
    airdrop(oldFlipSnapshotFilename, parsedLog)


def snapshot(
    snapshot_blocknumber=web3.eth.block_number,
    rinkeby_flip_deployed="0xbFf4044285738049949512Bd46B42056Ce5dD59b",
    filename="snapshot.csv",
):
    logging.info("Taking snapshot in " + filename)

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
        ## This will break if snapshot_blocknumber < latestblock-100 due to infura free-plan limitation
        holderBalance = flipContract.functions.balanceOf(holder).call(
            block_identifier=snapshot_blocknumber
        )
        # HolderBalance>0 already filters out the zero address (when tokens are burnt)
        if holderBalance > 0:
            totalBalance += holderBalance
            holder_balances.append(holderBalance)
            holder_list.append(holder)

    # Health check
    assert len(holder_list) == len(holder_balances)
    ## This will break if snapshot_blocknumber < latestblock-100 due to infura free-plan limitation
    totalSupply = flipContract.functions.totalSupply().call(
        block_identifier=snapshot_blocknumber
    )
    assert totalSupply == totalBalance

    # Can be checked in Etherscan that the values match
    print(totalSupply)
    print(len(holder_list))

    # Add checksum for security purposes
    holder_list.append("TotalNumberHolders:" + str(len(holder_list)))
    holder_balances.append(totalBalance)
    rows = zip(holder_list, holder_balances)

    with open(filename, "w") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)

    print("Snapshot completed")
    logging.info("Snapshot completed in " + filename)


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


def airdrop(snapshot_csv, parsedLog):
    AUTONOMY_SEED = os.environ["SEED"]
    DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    print(f"DEPLOYER = {DEPLOYER}")

    logging.info("Doing airdrop of new FLIP")

    (
        holderAccountsOldFlip,
        holderBalancesOldFlip,
        totalSupplyOldFlip,
    ) = readCSVSnapshotChecksum(snapshot_csv)

    # Acccount running this script should receive the newFLIP amount necessary to do the airdrop
    # Change this to DEPLOYER when we want to run this in RINKEBY. Cannot use this in hardhat because the account has no eth
    # airdropper = DEPLOYER
    airdropper = accounts[0]

    ## If we have deployed some but not all we better redeploy them all. If all have been deployed, get their addresses.

    if "New set of contracts deployed" not in parsedLog:
        cf = deploy_set_Chainflip_contracts(
            airdropper, airdropper, KeyManager, Vault, StakeManager, FLIP, os.environ
        )

        newStakeManager = cf.stakeManager.address
        newVault = cf.vault.address
        newFlip = cf.flip.address
        newKeyManager = cf.keyManager.address

        listOfTx = []

        logging.info("New set of contracts deployed")
        logging.info("StakeManager address:" + newStakeManager)
        logging.info("Vault address:" + newVault)
        logging.info("FLIP address:" + newFlip)
        logging.info("KeyManager address:" + newKeyManager)
    else:
        # This should never happen twice so we can parse it like this
        index = parsedLog.index("New set of contracts deployed")
        newStakeManager = parsedLog[index + 1].split(":")[1]
        newVault = parsedLog[index + 2].split(":")[1]
        newFlip = parsedLog[index + 3].split(":")[1]
        newKeyManager = parsedLog[index + 4].split(":")[1]

        # Get all previous pending transactions and check that they have been completed

        # TO DO: This should probably be parsed for all lines, there could be transactions in different parts of the log

        # Remove square parenthesis
        strOfTxx = parsedLog[index + 5][1:-1]
        listOfTx = strOfTxx.split(", ")
        for i in range(len(listOfTx)):
            # Remove surrounding commas
            listOfTx[i] = listOfTx[i][1:-1]
            # Check that they have been completed before continuing
            web3.eth.wait_for_transaction_receipt(listOfTx[i])

        # TO DO: Remove this, only used for development purposes
        logging.info(listOfTx)

    # OldFlipSupply is greater than new FLIP INIT Supply. For the airdrop we will airdrop tokens to all non-stakeManager accounts and
    # get to a state where newStakeManager's new flip balance is lower than oldStakeManager's old flip balance.
    # The difference can be minted by the state chain via updateTokenSupply.

    # Do Airdrop

    with open("build/contracts/FLIP.json") as f:
        info_json = json.load(f)
    abi = info_json["abi"]

    newFlipContract = web3.eth.contract(address=newFlip, abi=abi)
    # To check if transaction has already been made before, even if brownie has not caught it.
    events = list(
        fetch_events(
            newFlipContract.events.Transfer,
            from_block=0,
            to_block=web3.eth.block_number,
        )
    )

    skip_receivers = []
    print(
        "Got",
        len(events),
        "transfers already performed from airdropper to old FLIP holders",
    )

    # Get list of unique addresses that have recieved new FLIP from the airdropper
    # This will contain newly deployed stakeManager, the airdropper itself and receivers from this script previously been run.
    # Technically there could be transactions pending in the mempool - should we instead keep track of sent transactions? Then we have issues if tx's are not mined
    for event in events:
        toAddress = event.args.to
        fromAddress = event.args["from"]
        # Should already be unique but just in case
        if toAddress not in skip_receivers:
            skip_receivers.append(toAddress)

    # Skip receivers contain airdropper, newStakeManager and any address that has already received it.
    # Also, do not transfer to: oldStakeManager and oldFlipDeployer
    # even if Airdropper == oldFlipDeployer it can be skipped, since airdropper will keep remaining tokens
    skip_receivers.append(rinkeby_sm_deployed)
    skip_receivers.append(oldFlipDeployer)

    listOfTxSent = []
    for i in range(len(holderAccountsOldFlip)):
        # When in rinkeby we should add .transact() and wait for a receipt? Or send all transactions and then check them afterwards
        receiverNewFlip = holderAccountsOldFlip[i]
        if receiverNewFlip not in skip_receivers:
            # When sending a public transaction we need transact and it requires a string as the address sender (not account)
            tx = newFlipContract.functions.transfer(
                receiverNewFlip, int(holderBalancesOldFlip[i])
            ).transact({"from": str(airdropper)})
            # # Waiting for the receipt - will be slower but in case we need to rerun it we won't have to wait for mempool transactions
            # web3.eth.wait_for_transaction_receipt(tx)
            # print ("Transfer to " + receiverNewFlip +" completed")
            listOfTxSent.append(tx.hex())

    if len(listOfTxSent) != 0:
        logging.info(listOfTxSent)

    return newFlip, newStakeManager


def readCSVSnapshotChecksum(snapshot_csv):
    # Read csv file
    read_snapshot_csv = open(snapshot_csv, "r")
    holderAccounts = []
    holderBalances = []
    totalBalance = 0

    # Split columns while reading
    for a, b in csv.reader(read_snapshot_csv, delimiter=","):
        if "TotalNumberHolders:" not in a:
            # Append each variable to a separate list
            holderAccounts.append(a)
            holderBalances.append(b)
            totalBalance += int(b)
        else:
            # Checksum in the last row
            print("Checksum verification")
            numberHolders = a.split(":")
            assert int(numberHolders[1]) == len(holderAccounts)
            assert totalBalance == int(b)

    # Printing for visibility purposes - amount has been checked
    print(snapshot_csv)
    print(totalBalance)
    print(len(holderAccounts))

    return (holderAccounts, holderBalances, totalBalance)


def verifyAirdrop(initalSnapshot, airdropSnapshot):
    (
        oldFlipHolderAccounts,
        oldFlipholderBalances,
        oldFliptotalBalance,
    ) = readCSVSnapshotChecksum(initalSnapshot)
    (
        newFLIPHolderAccounts,
        newFLIPholderBalances,
        newFLIPtotalBalance,
    ) = readCSVSnapshotChecksum(airdropSnapshot)

    # As mentioned before, newFLIPHolderAccounts will have two extra holders - newStakeManager and deployer which will be the first two lines
    # - FLIP gives new flip to StakeManager and airdropper so airdropper will appear in the new snapshot -> Pass address of old StakeManager and give that balance to the new StakeManager

    # A pain to verify so commented for now
    # assert newFLIPHolderAccounts[0] == cf.flip.balanceOf(newStakeManager)
    assert newFLIPHolderAccounts[1] == accounts[0]

    # Delete both holders
    del newFLIPHolderAccounts[0:2]
    del newFLIPholderBalances[0:2]

    # We will be able to compare oldFliptotalBalance with newFLIPtotalBalance whenever we can set the INIT_SUPPLY when deploying FLIP
    assert len(oldFlipHolderAccounts) == len(newFLIPHolderAccounts)
    assert len(oldFlipholderBalances) == len(newFLIPholderBalances)

    for i in range(len(oldFlipHolderAccounts)):
        # Cannot compare pure balances here since oldHolders are in Rinkeby and new ones local
        assert oldFlipHolderAccounts[i] == newFLIPHolderAccounts[i]
        assert oldFlipholderBalances[i] == newFLIPholderBalances[i]
