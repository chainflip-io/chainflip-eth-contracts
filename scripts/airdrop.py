import sys
import os
import json
import csv
import logging
import os.path
import math

sys.path.append(os.path.abspath("tests"))
from consts import ZERO_ADDR, INIT_SUPPLY, E_18
from brownie import chain, accounts, StateChainGateway, FLIP, web3, network, MultiSend
from web3._utils.events import get_event_data
from web3._utils.filters import construct_event_filter_params


logname = "airdrop.log"
logging.basicConfig(filename=logname, level=logging.INFO)


# -------------------- Airdrop specific parmeters -------------------- #
oldStakeManager = "0xff99F65D0042393079442f68F47C7AE984C3F930"
oldFlipDeployer = "0xa56A6be23b6Cf39D9448FF6e897C29c41c8fbDFF"
goerliOldFlip = "0x8e71CEe1679bceFE1D426C7f23EAdE9d68e62650"
oldFlipSnapshotFilename = "snapshotOldFlip.csv"
# Adding a buffer of 10 blocks. Setting this instead of zero
# as no event swill have been emitted before the deployment
oldFlip_deployment_block = 7727329 - 10

# NOTE: These addresses are for a fresh hardhat network. To update.
newFlip = "0x10C6E9530F1C1AF873a391030a1D9E8ed0630D26"
newStateChainGateway = "0xeEBe00Ac0756308ac4AaBfD76c05c4F3088B8883"
# -------------------------------------------------------------------- #


userInputConfirm = ["", "y", "Y", "yes", "Yes", "YES"]
snapshotSuccessMessage = "Snapshot taken and succesfully stored in "
startAirdropMessage = "Starting airdrop of new FLIP"
airdropScGatewaySuccess = "Airdrop to ScGateway sent and confirmed!"
airdropSuccessMessage = "😎  Airdrop transactions sent and confirmed! 😎"
multiSendDeploySuccessMessage = "MultiSend deployed at: "

# Amount of transfers per transaction so we don't reach gas limit
transfer_batch_size = 200

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
        assert chain.id == 5 or chain.id == 31337, logging.error(
            "Wrong chain. Should be running in goerli"
        )
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

    # Deploy a Multisend if there isn't a deployed one.
    multiSend_address = None

    for line in parsedLog:
        if multiSendDeploySuccessMessage in line:
            _, multiSend_address = line.split(multiSendDeploySuccessMessage, 1)
            printAndLog("MultiSend already deployed")
            break

    if multiSend_address == None:
        deployMultiSend = input("Deploy MultiSend contract? (y)/n : ")
        if deployMultiSend not in userInputConfirm:
            printAndLog("Script stopped by user")
            return False
        multiSend = MultiSend.deploy(
            {"from": airdropper, "required_confs": 1},
        )
        printAndLog(multiSendDeploySuccessMessage + str(multiSend.address))
        multiSend_address = multiSend.address

    # Skip airdrop if it is logged succesfully. However, call Airdrop if it has failed at any point before the
    # succesful logging so all sent transactions are checked and we do the remaining airdrop transfers (if any)
    if not airdropSuccessMessage in parsedLog:
        # Inform the user if we are starting or continuing the airdrop
        printAndLog("Airdropper account: " + str(airdropper))
        if startAirdropMessage in parsedLog:
            inputString = (
                "Do you want to continue the previously started airdrop? (y)/n : "
            )
        else:
            inputString = "Do you want to start the airdrop? (y)/n : "
        doAirdrop = input(inputString)
        if doAirdrop not in ["", "y", "Y", "yes", "Yes"]:
            printAndLog("Script stopped by user")
            return False

        airdrop(
            airdropper,
            oldFlipSnapshotFilename,
            newFlip,
            newStateChainGateway,
            airdropScGatewaySuccess not in parsedLog,
            multiSend_address,
        )
    else:
        printAndLog("Skipped Airdrop - already completed succesfully")

    # Always verify Airdrop even if we have already run it before
    verifyAirdrop(
        airdropper,
        oldFlipSnapshotFilename,
        newFlip,
        newStateChainGateway,
        multiSend_address,
    )


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
            assert balance == oldFlipContract.balanceOf(
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
    totalSupply = oldFlipContract.totalSupply(block_identifier=snapshot_blocknumber)
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
def airdrop(
    airdropper,
    snapshot_csv,
    newFlip,
    newStateChainGateway,
    airdrop_scGateway,
    multiSend_address,
):
    printAndLog("Starting airdrop process")

    (
        oldFlipHolderAccounts,
        oldFlipholderBalances,
        oldFliptotalSupply,
        oldStateChainGatewayBalance,
        oldFlipDeployerBalance,
    ) = readCSVSnapshotChecksum(snapshot_csv)

    newFlipContract, newFlipContractObject = getContractFromAddress(newFlip)

    # Craft list of addresses that should be skipped when airdropping. Skip following receivers: airdropper,
    # newStateChainGateway, oldStateChainGateway and oldFlipDeployer. Also skip receivers that have already received
    # their airdrop. OldFlipDeployer can be the same as airdropper, that should be fine.
    skip_receivers_list = [
        str(airdropper),
        newStateChainGateway,
        oldStakeManager,
        oldFlipDeployer,
    ]

    listAirdropTXs, stateChainGatewayMinted = getTXsAndMintBalancesFromTransferEvents(
        airdropper, newFlipContractObject, newStateChainGateway, multiSend_address
    )

    if airdrop_scGateway:
        doAirdrop = input("Airdropping to ScGateway. Continue? (y/n): ")
        if doAirdrop not in ["", "y", "Y", "yes", "Yes"]:
            printAndLog("Script stopped by user")
            sys.exit("Script stopped by user")

        # Assertion for extra check in our particular case - just before we start all the aidrop => oldSupply < newSupply.
        assert oldFliptotalSupply < INIT_SUPPLY
        assert INIT_SUPPLY == newFlipContract.totalSupply()

        newStateChainGatewayBalance = newFlipContract.balanceOf(newStateChainGateway)
        # Assert that the balance of the SM has not changed before doing the final airdrop tx. No other TX should have been sent to
        # the StateChain. Technically a user could have sent FLIP there to screw this up, but in practice that won't happen. Also we
        # can just rerun the script if that were to happen.
        assert newStateChainGatewayBalance == stateChainGatewayMinted

        # The difference of supply must end up in the newStateChainGateway as that is the account where mint/burn tokens will be done.
        supplyDifference = INIT_SUPPLY - oldFliptotalSupply

        stateChainGatewayBalanceDifference = (
            oldStateChainGatewayBalance - newStateChainGatewayBalance
        )

        # New statechain should only have the genesis tokens
        assert stateChainGatewayBalanceDifference > 0
        assert stateChainGatewayBalanceDifference > supplyDifference

        printAndLog("Doing transfer from airdropper to StateChainGateway")
        # Transfer the difference between the stateChainGateway difference and the newFlipTobeMinted later on by the State chain
        # Also should work if newFlipToBeMinted < 0. We need to transfer that extra amount so the stateChain can burn it later.
        amountToTransferToScG = stateChainGatewayBalanceDifference + supplyDifference
        assert (
            newStateChainGatewayBalance + amountToTransferToScG
        ) - oldStateChainGatewayBalance == supplyDifference

        # Check that the airdropper has the balance to airdrop
        assert newFlipContract.balanceOf(str(airdropper)) >= amountToTransferToScG

        # Adding extra confirmations to ensure that we get the updated balances for the checks
        tx = newFlipContract.transfer(
            newStateChainGateway,
            amountToTransferToScG,
            {"from": airdropper, "required_confs": 3},
        )
        logging.info("Airdrop transaction Tx Hash:" + tx.txid)

        assert (
            newFlipContract.balanceOf(str(newStateChainGateway))
            - oldStateChainGatewayBalance
            == supplyDifference
        )
        printAndLog(
            "Final balance of ScGateway div18:  "
            + str(newFlipContract.balanceOf(str(newStateChainGateway)) / E_18)
        )
        printAndLog(
            "ScGateway supply difference div18: " + str(supplyDifference / E_18)
        )
        printAndLog(airdropScGatewaySuccess)

    doAirdrop = input("Proceeding with airdrops to the users. Continue? (y/n): ")
    if doAirdrop not in ["", "y", "Y", "yes", "Yes"]:
        printAndLog("Script stopped by user")
        sys.exit("Script stopped by user")

    # Full list of addresses to skip - add already airdropped accounts
    for airdropTx in listAirdropTXs:
        skip_receivers_list.append(airdropTx[0])

    printAndLog(startAirdropMessage)

    # Build a list of transactions to send
    listOfTxtoSend = []
    skip_counter = 0
    totalAmount_toTransfer = 0
    for i in range(len(oldFlipHolderAccounts)):
        if oldFlipHolderAccounts[i] not in skip_receivers_list:
            listOfTxtoSend.append([oldFlipHolderAccounts[i], oldFlipholderBalances[i]])
            totalAmount_toTransfer += int(oldFlipholderBalances[i])
        else:
            # Logging only in debug level
            printAndLog("Skipping receiver:" + str(oldFlipHolderAccounts[i]))
            skip_counter += 1

    # Check that the airdropper has the balance to airdrop for the loop airdrop transfer (remaining Txs)
    assert newFlipContract.balanceOf(str(airdropper)) >= totalAmount_toTransfer

    listOfTxSent = []

    multiSend = MultiSend.at(multiSend_address)

    # Approve the entire amount in one call
    newFlipContract.approve(
        multiSend.address, totalAmount_toTransfer, {"from": airdropper}
    )

    # Iterate over batches of 200 lists
    for i in range(0, len(listOfTxtoSend), transfer_batch_size):
        transfer_batches = listOfTxtoSend[i : i + transfer_batch_size]
        # Process the batch
        total_transfer_batch = 0
        for transfer in transfer_batches:
            total_transfer_batch += int(transfer[1])

        # NOTE: This might not work when running a local hardhat fork. There is some error that
        # the nonce is too low. It's probably a HH bug, it's not a problem in a fresh hardhat
        # network nor in a live network.
        tx = multiSend.multiSendToken(
            newFlipContract,
            transfer_batches,
            total_transfer_batch,
            {"from": airdropper},
        )
        # Logging each individually - if logged at the end of the loop and it breaks before that, then transfers won't be logged
        logging.info("Airdrop transaction Tx Hash:" + tx.txid)

        listOfTxSent.append(tx.txid)

    assert newFlipContract.allowance(airdropper, multiSend.address) == 0
    assert newFlipContract.balanceOf(multiSend.address) == 0
    assert len(listOfTxSent) == int(
        math.ceil(len(listOfTxtoSend) / transfer_batch_size)
    )

    # Should have skipped oldStateChainGateway and oldFlipDeployer for sure. NewStateChainGateway might have
    # been airdropped depending on the airdrop_scGateway flag but won't be in the lists anyway.
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
def verifyAirdrop(
    airdropper, initalSnapshot, newFlip, newStateChainGateway, multiSend_address
):

    printAndLog("Verifying airdrop")

    newFlipContract, newFlipContractObject = getContractFromAddress(newFlip)

    totalSupplyNewFlip = newFlipContract.totalSupply(
        block_identifier=web3.eth.block_number
    )

    assert totalSupplyNewFlip == INIT_SUPPLY

    (listAirdropTXs, _) = getTXsAndMintBalancesFromTransferEvents(
        airdropper, newFlipContractObject, newStateChainGateway, multiSend_address
    )

    # Check list of receivers and amounts against old FLIP snapshot csv file
    (
        oldFlipHolderAccounts,
        oldFlipholderBalances,
        oldFliptotalSupply,
        oldStateChainGatewayBalance,
        oldFlipDeployerBalance,
    ) = readCSVSnapshotChecksum(initalSnapshot)

    # Minus two oldFlipHolders - we don't airdrop to neither oldStateChainGateway nor oldFlipDeployer (could be same as airdropper)
    # Actually the default account has FLIP so when testing this could be 3 skipped addresses
    if airdropper in oldFlipHolderAccounts:
        len(listAirdropTXs) == len(oldFlipHolderAccounts) - 3
        index = oldFlipHolderAccounts.index(airdropper)
        oldFlipHolderAccounts.pop(index)
        oldFlipholderBalances.pop(index)
    else:
        len(listAirdropTXs) == len(oldFlipHolderAccounts) - 2

    # Remove oldStateChainGateway and oldFliperDeployer
    del oldFlipHolderAccounts[0:2]
    del oldFlipholderBalances[0:2]

    # Sanity check - this could potentially fail if the batch transfers have been broken and it has ended up
    # doing a different amount of batches than if it had all succeeded.
    assert int(math.ceil(len(listAirdropTXs) / transfer_batch_size)) == int(
        math.ceil(len(oldFlipHolderAccounts) / transfer_batch_size)
    )

    # oldFlipHolderAccounts is ordered so we can break as soon as an amount is < cutoff_amount
    # It is check that oldFlipHolders have been airdropped the correct amount
    cutoff_amount = 6000 * 10**18
    for (holder, balance) in zip(oldFlipHolderAccounts, oldFlipholderBalances):
        if int(balance) < cutoff_amount:
            continue
        else:
            airdrop_found = False
            for listAirdropTX in listAirdropTXs:
                if listAirdropTX[0] == str(holder):
                    assert listAirdropTX[1] == int(balance)
                    airdrop_found = True
                    break
            assert airdrop_found
            continue

    # Extra check
    assert (
        len(listAirdropTXs) == len(oldFlipHolderAccounts) == len(oldFlipholderBalances)
    )

    # Check that the final supply difference and that the difference is in the stateChainGateway
    # This should be the case regardless of Chainflip having burnt/mint FLIP from the stateChainGateway
    supplyDifference = oldFliptotalSupply - newFlipContract.totalSupply()
    assert supplyDifference == oldStateChainGatewayBalance - newFlipContract.balanceOf(
        newStateChainGateway
    )

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
    airdropper, flipContractObject, stateChainGateway, multiSend_address
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
    # Get all transfer events from the airdropper and the initial minting. MultiSend is used, so tx's
    # won't be from the airdropper but from the MultiSend
    for event in events:
        toAddress = event.args.to
        fromAddress = event.args["from"]
        amount = event.args.value
        # If there has been an airdrop to the stateChainGateway just account for the amount to make checking easier
        if fromAddress == str(airdropper) and toAddress == stateChainGateway:
            continue
        # Addresses should be unique but just in case
        elif fromAddress == str(multiSend_address) and (
            toAddress not in listAirdropTXs
        ):
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

    return listAirdropTXs, int(initialMintTXs[0][1])


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


def readCSVSnapshotChecksum(snapshot_csv):
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

    # We get the holder amounts ordered in a descending order
    # Health check that the biggest holder is the old FLIP deployer and the
    # second one is the StakeMangaer
    assert holderAccounts[0] == oldFlipDeployer, logging.error(
        "First holder should be the old flip deployer"
    )
    oldFlipDeployerBalance = holderBalances[0]
    assert holderAccounts[1] == oldStakeManager, logging.error(
        "Second holder should be the old StakeManager"
    )
    oldStakeManagerBalance = holderBalances[1]

    return (
        holderAccounts,
        holderBalances,
        int(totalSupply),
        int(oldStakeManagerBalance),
        int(oldFlipDeployerBalance),
    )
