import sys
import os
import json
import csv
import logging
import os.path

sys.path.append(os.path.abspath("tests"))
from consts import ZERO_ADDR, INIT_SUPPLY, E_18
from brownie import (
    chain,
    accounts,
    KeyManager,
    Vault,
    StakeManager,
    FLIP,
    web3,
)
from deploy import deploy_set_Chainflip_contracts
from web3._utils.events import get_event_data
from web3._utils.filters import construct_event_filter_params


logname = "only_airdrop.log"
logging.basicConfig(filename=logname, level=logging.INFO)


airdropReceiversFilename = "airdrop_receivers.csv"
amountToSend = 1000 * E_18
## TODO: Update this
newFlip = "0x23Fe11D10b6Db053Df8e316302D6fe7F675Bd2CC"

userInputConfirm = ["", "y", "Y", "yes", "Yes", "YES"]
airdropSuccessMessage = "😎  Airdrop transactions sent and confirmed! 😎"
startAirdropMessage = "Starting airdrop process"


def main():
    AUTONOMY_SEED = os.environ["SEED"]
    DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)
    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]

    airdropper = DEPLOYER

    # --------------------------- Start of the script logic  ----------------------------

    parsedLog = []
    # Start parsing log
    file = open(logname, "r")
    for line in file.readlines():
        # Only check info messages from previous run (disregard DEBUG and ERROR) and remove end of line
        infoMessage = line.rstrip("\n").split("INFO:root:")
        if len(infoMessage) > 1:
            parsedLog.append(infoMessage[1])

    logging.info(
        "=========================   Running only_airdrop.py script  =========================="
    )

    if airdropSuccessMessage in parsedLog:
        printAndLog("Skipped Airdrop - already completed succesfully")
    else:
        if startAirdropMessage in parsedLog:
            # Wait for previously sent transactions to complete (from a potential previous run)
            waitForLogTXsToComplete(parsedLog)
            inputString = (
                "Do you want to continue the previously started airdrop? (y)/n : "
            )
        else:
            inputString = "Do you want to start the airdrop? (y)/n : "

        # Inform the user if we are starting or continuing the airdrop
        printAndLog("Airdropper account: " + str(airdropper))
        doAirdrop = input(inputString)
        if doAirdrop not in ["", "y", "Y", "yes", "Yes"]:
            printAndLog("Script stopped by user")
            return False

        airdrop(airdropper, airdropReceiversFilename, newFlip)

    # Always verify Airdrop even if we have already run it before
    verifyAirdrop(
        airdropper,
        airdropReceiversFilename,
        newFlip,
    )


# --- Airdrop process ----
# 1- To make sure no holder is Airdropped twice we check all the newFLIP airdrop transfer events.
# Doing this instead of parsing logged transactions because brownie could have failed
# after sending a transaction and before logging it. Also, we cannot rely on a log file as
# a protection against airdropping twice.
# 3- Log every transaction id for traceability and for future runs.
# 5- Check that all transactions have been confirmed.
# 6- Log succesful airdrop message.
# -----------------------
def airdrop(airdropper, receiver_csv, newFlip):
    printAndLog(startAirdropMessage)

    receiverAccounts = readCSV(receiver_csv)

    newFlipContract, newFlipContractObject = getContractFromAddress(newFlip)

    listReceived, listAmounts = getTXsFromTransferEvents(
        airdropper, newFlipContractObject
    )

    listToRecieve = []

    skip_counter = 0

    # Check if any of the receivers has recieved an airdrop transaction before
    for i in range(len(receiverAccounts)):
        if receiverAccounts[i] not in listReceived or listAmounts[i] != amountToSend:
            # Receiver has not been airdropped
            listToRecieve.append(receiverAccounts[i])
        else:
            # Logging only in debug level
            logging.debug("Skipping receiver:" + str(receiverAccounts[i]))
            skip_counter += 1

    totalAmountToAirdrop = len(listToRecieve) * amountToSend

    airdropperBalance = newFlipContract.balanceOf.call(str(airdropper))

    # Check that the airdropper has the balance to airdrop for the loop airdrop transfer
    assert airdropperBalance >= totalAmountToAirdrop

    listOfTxSent = []

    for receiver in listToRecieve:
        # Send all the airdrop transfers without waiting for confirmation. We will wait for all the confirmations afterwards.
        tx = newFlipContract.transfer(
            receiver,
            amountToSend,
            {"from": airdropper, "required_confs": 0},
        )
        # Logging each individually - if logged at the end of the loop and it breaks before that, then transfers won't be logged
        logging.info("Airdrop transaction Tx Hash:" + tx.txid)
        # Keeping a list of txHashes and wait for all their receipts afterwards
        listOfTxSent.append(tx.txid)

    printAndLog("Total number of Airdrop transfers: " + str(len(listOfTxSent)))
    printAndLog("Skipped number of transfers: " + str(skip_counter))

    # After all tx's have been send wait for the receipts. This could break (or could have broken before) so extra safety mechanism is added when rerunning script
    printAndLog("Waiting for airdrop transactions to be confirmed..")
    for txSent in listOfTxSent:
        web3.eth.wait_for_transaction_receipt(txSent)

    printAndLog(airdropSuccessMessage)


# --- Verify Airdrop process ----
# 1- Read receiver csv
# 2- Get all the airdrop transfer events
# 3- Compare transfer events to the receiver accounts and amounts
# -------------------------------
def verifyAirdrop(airdropper, receiver_csv, newFlip):

    printAndLog("Verifying airdrop")

    newFlipContract, newFlipContractObject = getContractFromAddress(newFlip)

    listReceived, listAmounts = getTXsFromTransferEvents(
        airdropper, newFlipContractObject
    )

    receiverAccounts = readCSV(receiver_csv)

    # Check that all receivers have received the correct amount
    for receiver in receiverAccounts:
        assert receiver in listReceived
        index = listReceived.index(receiver)
        assert listAmounts[index] == amountToSend

    printAndLog("😎  Airdrop verified succesfully! 😎")


# ---------------------------- Utility functions ---------------------------- #


def printAndLog(text):
    print(text)
    logging.info(text)


def getContractFromAddress(flip_address):
    with open("build/contracts/FLIP.json") as f:
        info_json = json.load(f)
    abi = info_json["abi"]

    # Object to get the event interface from
    flipContractObject = web3.eth.contract(address=flip_address, abi=abi)

    # Flip Contract to make the calls to
    flipContract = FLIP.at(flip_address)

    return flipContract, flipContractObject


# ---------------------------------------
# Get all confirmed newFLIP transfer events from the airdropper to other addresses.
# ---------------------------------------
def getTXsFromTransferEvents(airdropper, flipContractObject):
    printAndLog("Getting all transfer events")
    events = list(
        fetch_events(
            flipContractObject.events.Transfer,
            from_block=0,
            to_block=web3.eth.block_number,
        )
    )

    listReceivers = []
    listAmounts = []

    # Get all transfer events from the airdropper and the initial minting.
    for event in events:
        toAddress = event.args.to
        fromAddress = event.args["from"]
        amount = event.args.value
        if fromAddress == str(airdropper) and (toAddress not in listReceivers):
            listReceivers.append(toAddress)
            listAmounts.append(amount)

    return (listReceivers, listAmounts)


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


def waitForLogTXsToComplete(parsedLog):
    printAndLog("Waiting for sent transactions to complete...")
    # Get all previous sent transactions (if any) from the log and check that they have been included in a block and we get a receipt back
    previouslySentTxList = []
    for line in parsedLog:
        parsedLine = line.split("Airdrop transaction Tx Hash:")
        if len(parsedLine) > 1:
            tx = parsedLine[1]
            receipt = web3.eth.wait_for_transaction_receipt(tx)
            # Logging these only if running in debug level
            logging.debug(
                "Previous transaction succesfully included in a block. Hash and receipt:"
            )
            logging.debug(receipt)


def readCSV(csv):
    printAndLog("Reading data from file: " + csv)

    # Read csv file
    read_csv = open(csv, "r")
    receiverAccounts = []

    # Split columns while reading
    for a in csv.reader(read_csv):
        assert len(a) == 1
        receiverAccounts.append(a[0])
    return receiverAccounts
