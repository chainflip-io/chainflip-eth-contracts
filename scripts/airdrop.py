import sys
import os
import json
import csv
import logging
import os.path

sys.path.append(os.path.abspath("tests"))
from consts import ZERO_ADDR, INIT_SUPPLY
from brownie import chain, accounts, StateChainGateway, FLIP, web3, network
from web3._utils.events import get_event_data
from web3._utils.filters import construct_event_filter_params


logname = "airdrop.log"
logging.basicConfig(filename=logname, level=logging.INFO)

goerliOldStateChainGateway = "0xff99F65D0042393079442f68F47C7AE984C3F930"
oldFlipDeployer = "0xa56A6be23b6Cf39D9448FF6e897C29c41c8fbDFF"
goerliOldFlip = "0x8e71CEe1679bceFE1D426C7f23EAdE9d68e62650"
oldFlipSnapshotFilename = "snapshotOldFlip.csv"
# Adding a buffer of 10 blocks. Setting this instead of zero
# as no event swill have been emitted before the deployment
oldFlip_deployment_block = 7727329 - 10

# TODO: These addresses are for debugging. To update.
newFlip = "0xc0a3730FB678748a95dDFf99961F7a6B19F31583"
newStateChainGateway = "0xD9913A3BA5C48808F854DaB4F19DB0ffE6236722"

userInputConfirm = ["", "y", "Y", "yes", "Yes", "YES"]
snapshotSuccessMessage = "Snapshot taken and succesfully stored in "
airdropSuccessMessage = "😎  Airdrop transactions sent and confirmed! 😎"

# Set the priority fee for all transactions
network.priority_fee("1 gwei")

# Set SNAPSHOT_BLOCKNUMBER environment variable if we want to take the snapshot on a particular block
def main():
    AUTONOMY_SEED = os.environ["SEED"]
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)
    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]

    airdropper = DEPLOYER

    # If using Infura it will break if snapshot_blocknumber < latestblock-100 due to free-plan limitation
    # Use alchemy when running the old flip snapshot function
    snapshot_blocknumber = os.environ.get("SNAPSHOT_BLOCKNUMBER")

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
        "=========================   Running airdrop.py script  =========================="
    )

    # Do oldFlip snapshot if it is has not been logged or if the snapshot csv doesn't exist
    if (not snapshotSuccessMessage + oldFlipSnapshotFilename in parsedLog) or (
        not os.path.exists(oldFlipSnapshotFilename)
    ):
        assert chain.id == 5, logging.error("Wrong chain. Should be running in goerli")
        printAndLog(
            "Old FLIP snapshot not taken previously. Snapshot Blocknumber set to "
            + str(snapshot_blocknumber)
        )
        # if snapshot blocknumber not set, take it on the latest block
        if snapshot_blocknumber == None:
            snapshot_blocknumber = web3.eth.block_number
            printAndLog(
                "Latest block is "
                + str(snapshot_blocknumber)
                + ". Use it as snapshot block number."
            )
        printAndLog("Address of token set to " + goerliOldFlip)
        takeSnapshot = input("Take snapshot? (y)/n : ")
        if takeSnapshot not in userInputConfirm:
            printAndLog("Script stopped by user")
            return False
        snapshot(int(snapshot_blocknumber), goerliOldFlip, oldFlipSnapshotFilename)
    else:
        printAndLog("Skipped old FLIP snapshot - snapshot already taken")

    # Skip airdrop if it is logged succesfully. However, call Airdrop if it has failed at any point before the
    # succesful logging so all sent transactions are checked and we do the remaining airdrop transfers (if any)
    if not airdropSuccessMessage in parsedLog:
        # Inform the user if we are starting or continuing the airdrop
        printAndLog("Airdropper account: " + str(airdropper))
        if "Doing airdrop of new FLIP" in parsedLog:
            inputString = (
                "Do you want to continue the previously started airdrop? (y)/n : "
            )
        else:
            inputString = "Do you want to start the airdrop? (y)/n : "
        doAirdrop = input(inputString)
        if doAirdrop not in ["", "y", "Y", "yes", "Yes"]:
            printAndLog("Script stopped by user")
            return False

        airdrop(airdropper, oldFlipSnapshotFilename, newFlip, newStateChainGateway)
    else:
        printAndLog("Skipped Airdrop - already completed succesfully")

    # Always verify Airdrop even if we have already run it before
    verifyAirdrop(airdropper, oldFlipSnapshotFilename, newFlip, newStateChainGateway)


# Take a snapshot of all token holders and their balances at a certain block number. Store the data in a
# csv file. Last line is used as a checksum stating the total number of holders and the total balance
def snapshot(
    snapshot_blocknumber,
    goerliOldFlip,
    filename,
):
    (oldFlipContract, oldFlipContractObject) = getContractFromAddress(goerliOldFlip)
    # It will throw an error if there are more than 10.000 events (free Infura Limitation)
    # Split it if that is the case - there is no time requirement anyway

    # lets do a fetch every 10000 blocks - in total it's around 1,3M blocks. That's to avoid
    # the providers 10k limits
    step = 10000
    next_block = oldFlip_deployment_block + step
    from_block = oldFlip_deployment_block

    events = []

    while True:
        print(
            "Fetching events from block " + str(from_block) + " to " + str(next_block)
        )
        new_events = list(
            fetch_events(
                oldFlipContractObject.events.Transfer,
                from_block=from_block,
                to_block=next_block,
            )
        )
        events.extend(new_events)

        if next_block == snapshot_blocknumber:
            break
        else:
            # Both from & to_block are inclusive
            from_block = next_block + 1
            next_block += step
            if next_block > snapshot_blocknumber:
                next_block = snapshot_blocknumber

    # Alternative to avoid the slow getBalance calls which take hourse
    print("Number of events to be processed: ", len(events))
    totalBalance = 0
    holder_dict = {}
    for event in events:
        if event.args["value"] == 0:
            continue

        if event.args["from"] != "0x0000000000000000000000000000000000000000":
            holder_dict[event.args["from"]] -= event.args["value"]
            assert holder_dict[event.args["from"]] >= 0
            if holder_dict[event.args["from"]] == 0:
                del holder_dict[event.args["from"]]
        else:
            totalBalance += event.args["value"]

        if event.args["to"] != "0x0000000000000000000000000000000000000000":
            holder_dict[event.args["to"]] = (
                holder_dict.get(event.args["to"], 0) + event.args["value"]
            )
            assert holder_dict[event.args["to"]] > 0
        else:
            totalBalance -= event.args["value"]

    sorted_dict = dict(sorted(holder_dict.items(), key=lambda x: x[1], reverse=True))

    # Verify that at least the most relevant accounts' balances are correct
    print("Verifying balances of top holders")

    cutoff_amount = 6000 * 10**18
    for holder, balance in sorted_dict.items():
        if balance < cutoff_amount:
            break
        else:
            assert balance == oldFlipContract.balanceOf.call(
                holder, block_identifier=snapshot_blocknumber
            )

    holder_list = list(sorted_dict.keys())
    holder_balances = list(sorted_dict.values())

    # NOTE: Not using this as the balanceOf call is too slow
    # print("Processing events")
    # print("Total events: " + str(len(events)))
    # # Get list of unique addresses that have recieved FLIP
    # receiver_list = []
    # for event in events:
    #     toAddress = event.args.to
    #     if toAddress not in receiver_list:
    #         receiver_list.append(toAddress)
    # holder_balances = []
    # totalBalance = 0

    # # Get balances of receivers and check if they are holders. Balances need to be obtained at
    # # the same snapshot block number
    # print("Getting balances")
    # print("Number of unique receivers: " + str(len(receiver_list)))
    # holder_list = []
    # for index, holder in enumerate(receiver_list):
    #     print("Processing holder ",index)
    #     holderBalance = oldFlipContract.balanceOf.call(
    #         holder, block_identifier=snapshot_blocknumber
    #     )
    #     if holderBalance > 0:
    #         totalBalance += holderBalance
    #         holder_balances.append(holderBalance)
    #         holder_list.append(holder)

    # Health check
    assert len(holder_list) == len(holder_balances)
    totalSupply = oldFlipContract.totalSupply.call(
        block_identifier=snapshot_blocknumber
    )
    assert totalSupply == totalBalance

    # Can be checked against Etherscan that the values match
    printAndLog(
        "Old Flip total supply: "
        + str(totalSupply)
        + ". Should match Etherscan for block number: "
        + str(snapshot_blocknumber)
    )
    printAndLog(
        "Number of Old Flip holders: "
        + str(len(holder_list))
        + ". Should match Etherscan for block number: "
        + str(snapshot_blocknumber)
    )

    # Add checksum for security purposes
    holder_list.append("TotalNumberHolders:" + str(len(holder_list)))
    holder_balances.append(totalBalance)
    rows = zip(holder_list, holder_balances)

    printAndLog("Writing data into csv file")
    with open(filename, "w") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)

    printAndLog(snapshotSuccessMessage + filename)


# --- Airdrop process ----
# 1- Craft a list of addresses that should not receive an airdrop or that have already receieved it.
# To make sure no holder is Airdropped twice we check all the newFLIP airdrop transfer events.
# Doing this instead of parsing logged transactions because brownie could have failed
# after sending a transaction and before logging it. Also, we cannot rely on a log file as
# a protection against airdropping twice.
# 2- Loop through the oldFLIP holders list and airdrop them if they are not in the list of addresses to skip.
# 3- Log every transaction id for traceability and for future runs.
# 4- Check if there is a need to do ain airdrop to the newStateChainGateway due to totalSupply differences between old and new.
# 5- Check that all transactions have been confirmed.
# 6- Log succesful airdrop message.
# -----------------------
def airdrop(airdropper, snapshot_csv, newFlip, newStateChainGateway):
    printAndLog("Starting airdrop process")

    (
        oldFlipHolderAccounts,
        oldFlipholderBalances,
        oldFliptotalSupply,
        oldStateChainGatewayBalance,
        oldFlipDeployerBalance,
    ) = readCSVSnapshotChecksum(
        snapshot_csv, goerliOldStateChainGateway, oldFlipDeployer
    )

    newFlipContract, newFlipContractObject = getContractFromAddress(newFlip)

    # Craft list of addresses that should be skipped when aidropping. Skip following receivers: airdropper,
    # newStateChainGateway, oldStateChainGateway and oldFlipDeployer. Also skip receivers that have already received
    # their airdrop. OldFlipDeployer can be the same as airdropper, that should be fine.
    skip_receivers_list = [
        str(airdropper),
        newStateChainGateway,
        goerliOldStateChainGateway,
        oldFlipDeployer,
    ]

    (
        initialMintTXs,
        listAirdropTXs,
        newStateChainGatewayBalance,
        airdropperBalance,
    ) = getTXsAndMintBalancesFromTransferEvents(
        airdropper, newFlipContractObject, newStateChainGateway
    )

    # Check that the airdropper has the balance to airdrop for the loop airdrop transfer
    assert (
        airdropperBalance
        >= oldFliptotalSupply - oldStateChainGatewayBalance - oldFlipDeployerBalance
    )

    # Assertion for extra check in our particular case - just before we start all the
    # aidrop => oldSupply < newSupply.
    assert oldFliptotalSupply < INIT_SUPPLY

    # TODO: Make sure we are skipping the right addresses

    # Full list of addresses to skip - add already airdropped accounts
    for airdropTx in listAirdropTXs:
        skip_receivers_list.append(airdropTx[0])

    printAndLog("Starting airdrop of new FLIP")

    listOfTxSent = []
    skip_counter = 0
    for i in range(len(oldFlipHolderAccounts)):

        receiverNewFlip = oldFlipHolderAccounts[i]
        if receiverNewFlip not in skip_receivers_list:

            # Health check (not required)
            assert receiverNewFlip not in [
                str(airdropper),
                newStateChainGateway,
                goerliOldStateChainGateway,
                oldFlipDeployer,
            ]

            # Send all the airdrop transfers without waiting for confirmation. We will wait for all the confirmations afterwards.
            tx = newFlipContract.transfer(
                receiverNewFlip,
                int(oldFlipholderBalances[i]),
                {"from": airdropper, "required_confs": 0},
            )
            # Logging each individually - if logged at the end of the loop and it breaks before that, then transfers won't be logged
            logging.info("Airdrop transaction Tx Hash:" + tx.txid)
            # Keeping a list of txHashes and wait for all their receipts afterwards
            listOfTxSent.append(tx.txid)
        else:
            # Logging only in debug level
            logging.debug("Skipping receiver:" + str(receiverNewFlip))
            skip_counter += 1

    # TODO: Modify `airdropSuccessMessage` so in case of the below logic failing it doesn't start from the beginning
    # TODO: Think about this - how will the statechain min/burn tokens? Probably from the SCGateway - I think this is exactly what this
    # logic is doing.

    # OldFLIP supply is most likely different than the new initial flip supply (INIT_SUPPLY). We need to ensure that when minting the
    # supply difference the newStateChainGateway and oldStateChainGateway will end up with the same balance. If new State Chain Gateway has less balance
    # than the old one and the difference is bigger than the supply difference, we need to make an extra transfer from airdropper to the
    # new State Chain Gateway. This should be the case in this airdrop.
    # Technically it could be the case where some of newSupply tokens that will be minted would have to go to the airdroper, but that won't
    # be the case in this airdrop (and probably never).
    stateChainGatewayBalanceDifference = (
        oldStateChainGatewayBalance - newStateChainGatewayBalance
    )
    if (
        stateChainGatewayBalanceDifference > 0
        and stateChainGatewayBalanceDifference > newFlipToBeMinted
    ):
        printAndLog("Do extra transfer from airdropper to StateChainGateway")
        # Transfer the difference between the stateChainGateway difference and the newFlipTobeMinted later on by the State chain
        # Also should work if newFlipToBeMinted < 0. We need to transfer that extra amount so the stateChain can burn it later
        amountToTransfer = stateChainGatewayBalanceDifference - newFlipToBeMinted
        # Check that the airdropper has the balance to airdrop
        assert airdropperBalance >= amountToTransfer
        tx = newFlipContract.transfer(
            newStateChainGateway,
            amountToTransfer,
            {"from": airdropper, "required_confs": 0},
        )
        logging.info("Airdrop transaction Tx Hash:" + tx.txid)
        listOfTxSent.append(tx.txid)

    printAndLog("Total number of Airdrop transfers: " + str(len(listOfTxSent)))
    printAndLog(
        "Skipped number of transfers: "
        + str(skip_counter)
        + ". Should have skipped at least 2 (oldStateChainGateway and oldFlipDeployer)"
    )

    # After all tx's have been send wait for the receipts. This could break (or could have broken before) so extra safety mechanism is added when rerunning script
    printAndLog("Waiting for airdrop transactions to be confirmed..")
    for txSent in listOfTxSent:
        web3.eth.wait_for_transaction_receipt(txSent)

    printAndLog(airdropSuccessMessage)


# --- Verify Airdrop process ----
# 1- Read snapshot oldFLIP
# 2- Get all the airdrop transfer events
# 3- Compare transfer events to the snapshot holders balances
# 4- Check that the difference in supplies will be fixed when the newSupply is minted to the stateChainGateway
# -------------------------------
def verifyAirdrop(airdropper, initalSnapshot, newFlip, newStateChainGateway):

    printAndLog("Verifying airdrop")

    newFlipContract, newFlipContractObject = getContractFromAddress(newFlip)

    totalSupplyNewFlip = newFlipContract.totalSupply.call(
        block_identifier=web3.eth.block_number
    )

    assert totalSupplyNewFlip == INIT_SUPPLY

    (
        initialMintTXs,
        listAirdropTXs,
        newStateChainGatewayBalance,
        airdropperBalance,
    ) = getTXsAndMintBalancesFromTransferEvents(
        airdropper, newFlipContractObject, newStateChainGateway
    )

    # Check list of receivers and amounts against old FLIP snapshot csv file
    (
        oldFlipHolderAccounts,
        oldFlipholderBalances,
        oldFliptotalSupply,
        oldStateChainGatewayBalance,
        oldFlipDeployerBalance,
    ) = readCSVSnapshotChecksum(
        initalSnapshot, goerliOldStateChainGateway, oldFlipDeployer
    )

    # Minus two oldFlipHolders - we don't airdrop to neither oldStateChainGateway nor oldFlipDeployer (could be same as airdropper)
    assert len(listAirdropTXs) == len(oldFlipHolderAccounts) - 2

    # Remove oldStateChainGateway and oldFliperDeployer
    del oldFlipHolderAccounts[0:2]
    del oldFlipholderBalances[0:2]

    # Sanity check
    assert len(listAirdropTXs) == len(oldFlipHolderAccounts)

    # We cannot tell which order the transactions will be mined so we can't compare element by element.
    # However, accounts must be unique in the list, otherwise something has gone wrong in the airdrop and this will break.
    for airdropTx in listAirdropTXs:
        receiver = airdropTx[0]
        amountAirdropped = airdropTx[1]
        airdropperBalance -= amountAirdropped
        # This will throw an error automatically if it doesn't exist
        index = oldFlipHolderAccounts.index(receiver)
        oldFlipHolderAccounts.pop(index)
        amountOldFlipHolder = oldFlipholderBalances.pop(index)
        assert int(amountOldFlipHolder) == amountAirdropped

    # Check that all oldFlip Holders have been popped
    assert len(oldFlipHolderAccounts) == 0
    assert len(oldFlipholderBalances) == 0

    # No need to call it in a specific block since airdroper should have completed all airdrop transactions. Not really necessary but why not.
    airdropperRealBalance = newFlipContract.balanceOf.call(str(airdropper))
    assert airdropperBalance == airdropperRealBalance

    # Do final checking of stateChainGateway and airdropper balances
    newFlipToBeMinted = oldFliptotalSupply - INIT_SUPPLY

    # Check that when updateFlipSupply mints the remaining supply to the StateChainGateway the balances match.
    # Again, it could be the case where tokens would need to be airdropper to the stateChainGateway to be burnt, or that some of newSupply
    # tokens that will be minted would have to go to the airdroper, but that won't be the case in this airdrop (and probably never)
    assert (
        newStateChainGatewayBalance + newFlipToBeMinted == oldStateChainGatewayBalance
    )
    assert oldFlipDeployerBalance == airdropperBalance

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
# Get all confirmed newFLIP transfer events from the airdropper to other addresses. Also get the mint events.
# Then calculate the stateChainGateway and airdropper balance after mint. Account for a potential airdrop to the
# stateChainGateway to make up for the totalSupply difference - to make all the later checking easier.
# ---------------------------------------
def getTXsAndMintBalancesFromTransferEvents(
    airdropper, flipContractObject, stateChainGateway
):
    printAndLog("Getting all transfer events")
    events = list(
        fetch_events(
            flipContractObject.events.Transfer,
            from_block=0,
            to_block=web3.eth.block_number,
        )
    )

    listAirdropTXs = []
    initialMintTXs = []
    airdropedAmountToStateChainGateway = 0
    # Get all transfer events from the airdropper and the initial minting.
    for event in events:
        toAddress = event.args.to
        fromAddress = event.args["from"]
        amount = event.args.value
        # If there has been an airdrop to the stateChainGateway just account for the amount to make checking easier
        if fromAddress == str(airdropper) and toAddress == stateChainGateway:
            airdropedAmountToStateChainGateway = amount
        # Addresses should be unique but just in case
        elif fromAddress == str(airdropper) and (toAddress not in listAirdropTXs):
            listAirdropTXs.append([toAddress, amount])
        # Mint events
        elif fromAddress == ZERO_ADDR:
            initialMintTXs.append([toAddress, amount])

    # Check amounts against the newFlipDeployer(airdropper) and the newStateChainGateway
    assert len(initialMintTXs) == 2, logging.error("Minted more times than expected")

    # This should always apply so long as the FLIP contract has been deployed
    assert initialMintTXs[0][0] == stateChainGateway, logging.error(
        "First mint receiver should be the new State Chain Gateway"
    )
    stateChainGatewayMintBalance = (
        initialMintTXs[0][1] + airdropedAmountToStateChainGateway
    )
    assert initialMintTXs[1][0] == str(airdropper), logging.error(
        "First mint receiver should be the airdropper"
    )
    airdropperMintBalance = initialMintTXs[1][1] - airdropedAmountToStateChainGateway

    return (
        initialMintTXs,
        listAirdropTXs,
        int(stateChainGatewayMintBalance),
        int(airdropperMintBalance),
    )


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


def readCSVSnapshotChecksum(snapshot_csv, stateChainGateway, deployer):
    printAndLog("Reading snapshot from file: " + snapshot_csv)

    # Read csv file
    read_snapshot_csv = open(snapshot_csv, "r")
    holderAccounts = []
    holderBalances = []
    totalSupply = 0

    # Split columns while reading
    for a, b in csv.reader(read_snapshot_csv, delimiter=","):
        if "TotalNumberHolders:" not in a:
            # Append each variable to a separate list
            holderAccounts.append(a)
            holderBalances.append(b)
            totalSupply += int(b)
        else:
            # Checksum in the last row
            print("Checksum verification")
            numberHolders = a.split(":")
            assert int(numberHolders[1]) == len(holderAccounts)
            assert totalSupply == int(b)

    # TODO: This is now failing because we have ordered the amounts by holders. To be updated.
    # We can even add some extra check (e.g. call getFlip() from the ScGateway) to ensure we are
    # not doing anything wrong.

    # Assumption that we get the events in order, so first two events should be the initial mints
    assert holderAccounts[0] == stateChainGateway, logging.error(
        "First holder should be the State Chain Gateway"
    )
    stateChainGatewayBalance = holderBalances[0]
    assert holderAccounts[1] == deployer, logging.error(
        "Second holder should be the deployer"
    )
    deployerBalance = holderBalances[1]

    return (
        holderAccounts,
        holderBalances,
        int(totalSupply),
        int(stateChainGatewayBalance),
        int(deployerBalance),
    )
