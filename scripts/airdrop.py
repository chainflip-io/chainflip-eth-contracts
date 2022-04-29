import sys
import os
import json
import csv
import logging
import time
import os.path

sys.path.append(os.path.abspath("tests"))
from consts import ZERO_ADDR, INIT_SUPPLY
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


# This will continue logging at the end of the previous log (running .INFO for development purposes)
logname = "airdrop.log"

# TODO: Try to log at the same time on console and .log
logging.basicConfig(filename=logname, level=logging.INFO)
# logging.basicConfig(level=logging.INFO,handlers=[logging.FileHandler(logname), logging.StreamHandler()])

# In the end probably do this to log also all RPC calls but that will make it very unreadable
# logging.basicConfig(filename='airdrop.log', level=logging.DEBUG)
# So brownie can run a snapshot separately from airdrop

rinkeby_old_stakeManager = "0x3A96a2D552356E17F97e98FF55f69fDFb3545892"
oldFlipDeployer = "0x4D1951e64D3D02A3CBa0D0ef5438f732850ED592"
rinkeby_old_flip = "0xbFf4044285738049949512Bd46B42056Ce5dD59b"
oldFlipSnapshotFilename = "snapshot_old_flip.csv"
newFlipSnapshotFilename = "snapshot_new_flip.csv"


# Alternative way to handle assertions - for now we go with the other one.
# try:
#     assert chain.id == 4, "Wrong chain"
# except AssertionError:
#     logging.error ("Wrong chain")
#     raise


def main():
    # Using latest block for now as snapshot block
    # It will break if snapshot_blocknumber < latestblock-100 due to infura free-plan limitation
    snapshot_blocknumber = web3.eth.block_number

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

    # Do oldFlip snapshot if it is has not been logged or if the snapshot csv doesn't exist
    if (not "Snapshot completed in " + oldFlipSnapshotFilename in parsedLog) or (
        not os.path.exists(oldFlipSnapshotFilename)
    ):
        assert chain.id == 4, logging.error("Wrong chain. Should be running in Rinkeby")
        logging.info("Old FLIP snapshot not taken previously")
        snapshot(snapshot_blocknumber, rinkeby_old_flip, oldFlipSnapshotFilename)
    else:
        print("Skipped old FLIP snapshot - snapshop already taken")
        logging.info("Skipped old FLIP snapshot - snapshop already taken")

    # TODO: this is for development purposes to do the Airdrop in hardhat. To be removed
    assert chain.id > 10, logging.error(
        "Wrong chain. Should be running in local hardhat tesnet"
    )

    if not "😎  Airdrop completed! 😎" in parsedLog:
        # Inform the user if we are starting or continuing the airdrop and allow the user to only do a snapshot
        # without having to perform the airdrop
        if "Doing airdrop of new FLIP" in parsedLog:
            inputString = (
                "Do you want to continue the previously started airdrop? (Y)/N : "
            )
        else:
            inputString = "Do you want to start the airdrop? (Y)/N : "
        doAirdrop = input(inputString)
        if doAirdrop not in ["", "Y", "yes", "Yes"]:
            print("Script stopped")
            return False
        # Skip airdrop if it is logged as succesfully. However, call Airdrop if it has failed at any point before the
        # succesful logging so we do all the checking of sent transactions and do the remaining aidrop transfers (if any)
        (newStakeManager, newVault, newFlip, newKeyManager) = airdrop(
            oldFlipSnapshotFilename, parsedLog
        )
    else:
        logging.info("Skipped Airdrop - already completed succesfully")
        # If airdrop is completed then contracts should have succesfully been deployed and logged
        (
            newStakeManager,
            newVault,
            newFlip,
            newKeyManager,
        ) = getAndCheckDeployedAddresses(parsedLog)

    ##############################################################
    # TODO:Remove this, just to be able to visually look at it
    # Problem is if someone transfers the airdropped FLIP after airdrop and before snaphsot.
    ##############################################################
    if (not "Snapshot completed in " + newFlipSnapshotFilename in parsedLog) or (
        not os.path.exists(newFlipSnapshotFilename)
    ):
        snapshot(web3.eth.block_number, newFlip, newFlipSnapshotFilename)
    ##############################################################

    # Always verify Airdrop even if we have already runed it before.
    verifyAirdrop(oldFlipSnapshotFilename, newFlip, newStakeManager)


def snapshot(
    snapshot_blocknumber=web3.eth.block_number,
    rinkeby_old_flip="0xbFf4044285738049949512Bd46B42056Ce5dD59b",
    filename="snapshot.csv",
):
    logging.info("Taking snapshot in " + filename)

    # It will throw an error if there are more than 10.000 events (Infura Limitation)
    # Split it if that is the case - there is no time requirement anyway
    oldFlipContract = getContractFromAddress(rinkeby_old_flip)
    events = list(
        fetch_events(
            oldFlipContract.events.Transfer, from_block=0, to_block=snapshot_blocknumber
        )
    )

    # Get list of unique addresses that have recieved FLIP
    receiver_list = []
    for event in events:
        toAddress = event.args.to
        if toAddress not in receiver_list:
            receiver_list.append(toAddress)
    holder_balances = []
    totalBalance = 0

    # Get balances of receivers and check if they are holders
    holder_list = []
    for holder in receiver_list:
        holderBalance = oldFlipContract.functions.balanceOf(holder).call(
            block_identifier=snapshot_blocknumber
        )
        # HolderBalance>0 already filters out the zero address (when tokens are burnt)
        if holderBalance > 0:
            totalBalance += holderBalance
            holder_balances.append(holderBalance)
            holder_list.append(holder)

    # Health check
    assert len(holder_list) == len(holder_balances)
    totalSupply = oldFlipContract.functions.totalSupply().call(
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


def getContractFromAddress(flip_address):
    with open("build/contracts/FLIP.json") as f:
        info_json = json.load(f)
    abi = info_json["abi"]

    flipContract = web3.eth.contract(address=flip_address, abi=abi)
    return flipContract


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


def getAirdropper():
    AUTONOMY_SEED = os.environ["SEED"]
    DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    # print(f"DEPLOYER = {DEPLOYER}")

    # Acccount running this script should receive the newFLIP amount necessary to do the airdrop
    # Change this to DEPLOYER when we want to run this in RINKEBY. Cannot use this in hardhat because the account (SEED) has no eth
    # airdropper = DEPLOYER
    airdropper = accounts[0]

    return airdropper


def airdrop(snapshot_csv, parsedLog):

    airdropper = getAirdropper()

    logging.info("Doing airdrop of new FLIP")

    (
        oldFlipHolderAccounts,
        oldFlipholderBalances,
        oldFliptotalSupply,
        oldStakeManagerBalance,
        oldFlipDeployerBalance,
    ) = readCSVSnapshotChecksum(snapshot_csv, rinkeby_old_stakeManager, oldFlipDeployer)

    ## If we have deployed some but not all we better redeploy them all. If all have been deployed, get their addresses.
    ## TODO: What communityKey should we set here?
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
        # Ensure that contracts have been deployed and addresses are in the log
        (
            newStakeManager,
            newVault,
            newFlip,
            newKeyManager,
        ) = getAndCheckDeployedAddresses(parsedLog)

        # Get all previous sent transactions (if any) from the log and check that they have been included in a block and we get a receipt back
        previouslySentTxList = []
        for line in parsedLog:
            parsedLine = line.split("Airdrop transaction Tx Hash:")
            if len(parsedLine) > 1:
                previouslySentTxList.append(parsedLine[1])

        for tx in previouslySentTxList:
            receipt = web3.eth.wait_for_transaction_receipt(tx)
            # Logging these only if running in debug level
            logging.debug(
                "Previous transaction succesfully included in a block. Hash and receipt:"
            )
            logging.debug(receipt)

    # To make sure no holder is Airdropped twice we get all the newFLIP transfer events
    # Doing this instead of parsing logged transactions because brownie might potentially fail
    # after sending a transaction and before logging it. Also, when it comes to airdropping
    # protection against airdropping twice, we cannot rely on a log file.
    newFlipContract = getContractFromAddress(newFlip)

    # Craft list of addresses that should be skipped when aidropping.
    # Skip following receivers: airdropper, newStakeManager, oldStakeManager and oldFlipDeployer.
    # Also skip receivers that have already received their airdrop
    # OldFlipDeployer can be the same as airdropper, that's fine.
    skip_receivers_list = [
        str(airdropper),
        newStakeManager,
        rinkeby_old_stakeManager,
        oldFlipDeployer,
    ]

    (
        initialMintTXs,
        listAirdropTXs,
        newStakeManagerBalance,
        airdropperBalance,
    ) = getTXsAndBalancesFromTransferEvents(
        airdropper, newFlipContract, newStakeManager
    )

    # Check that the airdropper has the balance to airdrop for the loop airdrop transfer
    assert (
        airdropperBalance
        >= oldFliptotalSupply - oldStakeManagerBalance - oldFlipDeployerBalance
    )
    # Assertion for extra check in our particular case - just before we start all the airdrop
    newFlipToBeMinted = oldFliptotalSupply - INIT_SUPPLY
    assert newFlipToBeMinted > 0

    # Full list of addresses to skip - add already airdropped accounts
    for airdropTx in listAirdropTXs:
        skip_receivers_list.append(airdropTx[0])

    listOfTxSent = []
    skip_counter = 0
    for i in range(len(oldFlipHolderAccounts)):
        # When in rinkeby we should add .transact() and wait for a receipt? Or send all transactions and then check them afterwards
        receiverNewFlip = oldFlipHolderAccounts[i]
        if receiverNewFlip not in skip_receivers_list:

            # Health check (not required)
            assert receiverNewFlip not in [
                airdropper,
                newStakeManager,
                rinkeby_old_stakeManager,
                oldFlipDeployer,
            ]

            # When sending a public transaction we need transact() and it requires a string as the address sender (not account)
            tx = newFlipContract.functions.transfer(
                receiverNewFlip, int(oldFlipholderBalances[i])
            ).transact({"from": str(airdropper)})
            # Logging each individually - if logged at the end of the loop and it breaks before that, then transfers won't be logged
            logging.info("Airdrop transaction Tx Hash:" + tx.hex())
            # Keeping a list of txHashes to wait afterwards. Not waiting every after transaction because it has no benefit and it would take long
            listOfTxSent.append(tx.hex())
        else:
            # Logging only in debug level
            logging.debug("Skipping receiver:" + str(receiverNewFlip))
            skip_counter += 1

    # Ensure that newStakeManager and oldStakeManager end up with the same balance. If new Stake Manager has less balance than the old one
    # and the difference is bigger than the supply difference, we need to make an extra transfer from airdropper to the new Stake Manager.
    # This should be the case in this airdrop.

    # Technically it could be the case where tokens would need to be airdropped to the stakeManager to be burnt, or that some of newSupply
    # tokens that will be minted would have to go to the airdroper, but that won't be the case in this airdrop (and probably never)
    stakeManagerBalanceDifference = oldStakeManagerBalance - newStakeManagerBalance
    if (
        stakeManagerBalanceDifference > 0
        and stakeManagerBalanceDifference > newFlipToBeMinted
    ):
        print("Do extra transfer from airdropper to StakeManager")
        # Transfer the difference between the stakeManager difference and the newFlipTobeMinted later on by the State chain
        # Also should work if newFlipToBeMinted < 0. We need to transfer that extra amount so the stateChain can burn it later
        amountToTransfer = stakeManagerBalanceDifference - newFlipToBeMinted
        # Check that the airdropper has the balance to airdrop
        assert airdropperBalance >= amountToTransfer
        tx = newFlipContract.functions.transfer(
            newStakeManager, amountToTransfer
        ).transact({"from": str(airdropper)})
        logging.info("Airdrop transaction Tx Hash:" + tx.hex())
        listOfTxSent.append(tx.hex())

    logging.info("Total number of Airdrop transfers: " + str(len(listOfTxSent)))
    logging.info(
        "Skipped number of transfers: " + str(skip_counter) + " should skip at least 2"
    )

    print("Total number of Airdrop transfers: " + str(len(listOfTxSent)))
    print("Skiped a total of " + str(skip_counter))

    # After all tx's have been send wait for the receipts. This could break (or could have broken before) so extra safety mechanism added when rerunning script
    for txSent in listOfTxSent:
        web3.eth.wait_for_transaction_receipt(txSent)

    print("😎  Airdrop completed! 😎 \n")
    logging.info("😎  Airdrop completed! 😎")

    return (newStakeManager, newVault, newFlip, newKeyManager)


def readCSVSnapshotChecksum(snapshot_csv, stakeManager, deployer):
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

    # Printing for visibility purposes - amount has been checked
    print(snapshot_csv)
    print(totalSupply)
    print(len(holderAccounts))

    # Assumption that we get the events in order, so first two events should be the initial mints
    assert holderAccounts[0] == stakeManager, logging.error(
        "First holder should be the Stake Manager"
    )
    stakeManagerBalance = holderBalances[0]
    assert holderAccounts[1] == deployer, logging.error(
        "Second holder should be the deployer"
    )
    deployerBalance = holderBalances[1]

    return (
        holderAccounts,
        holderBalances,
        int(totalSupply),
        int(stakeManagerBalance),
        int(deployerBalance),
    )


def getTXsAndBalancesFromTransferEvents(airdropper, flipContract, stakeManager):
    events = list(
        fetch_events(
            flipContract.events.Transfer,
            from_block=0,
            to_block=web3.eth.block_number,
        )
    )

    listAirdropTXs = []
    initialMintTXs = []
    airdropedAmountToStakeManager = 0
    # Get all transfer events from the airdropper and the initial minting.
    for event in events:
        toAddress = event.args.to
        fromAddress = event.args["from"]
        amount = event.args.value
        # If there has been an airdrop to the stakeManager do not include it (just account for the amount) - makes checking easier
        if fromAddress == airdropper and toAddress == stakeManager:
            airdropedAmountToStakeManager = amount
        # Addresses should be unique but just in case
        elif fromAddress == airdropper and (toAddress not in listAirdropTXs):
            listAirdropTXs.append([toAddress, amount])
        elif fromAddress == ZERO_ADDR:
            initialMintTXs.append([toAddress, amount])

    # Check amounts against the newFlipDeployer(airdropper) and the newStakeManager
    assert len(initialMintTXs) == 2, logging.error("Minted more times than expected")

    # This should always apply so long as the FLIP contract has been deployed
    assert initialMintTXs[0][0] == stakeManager, logging.error(
        "First mint receiver should be the new Stake Manager"
    )
    stakeManagerBalance = initialMintTXs[0][1] + airdropedAmountToStakeManager
    assert initialMintTXs[1][0] == airdropper, logging.error(
        "First mint receiver should be the airdropper"
    )
    airdropperBalance = initialMintTXs[1][1] - airdropedAmountToStakeManager

    return (
        initialMintTXs,
        listAirdropTXs,
        int(stakeManagerBalance),
        int(airdropperBalance),
    )


def verifyAirdrop(initalSnapshot, newFlip, newStakeManager):

    logging.info("Verifying airdrop")
    airdropper = getAirdropper()

    newFlipContract = getContractFromAddress(newFlip)

    totalSupplyNewFlip = newFlipContract.functions.totalSupply().call(
        block_identifier=web3.eth.block_number
    )

    assert totalSupplyNewFlip == INIT_SUPPLY

    (
        initialMintTXs,
        listAirdropTXs,
        newStakeManagerBalance,
        airdropperBalance,
    ) = getTXsAndBalancesFromTransferEvents(
        airdropper, newFlipContract, newStakeManager
    )

    # Check list of receivers and amounts against old FLIP snapshot csv file
    (
        oldFlipHolderAccounts,
        oldFlipholderBalances,
        oldFliptotalSupply,
        oldStakeManagerBalance,
        oldFlipDeployerBalance,
    ) = readCSVSnapshotChecksum(
        initalSnapshot, rinkeby_old_stakeManager, oldFlipDeployer
    )

    print(len(listAirdropTXs))
    print(len(oldFlipHolderAccounts) - 2)
    # Minus two oldFlipHolders - we don't airdrop to neither oldStakeManager nor oldFlipDeployer (could be same as airdropper)
    assert len(listAirdropTXs) == len(oldFlipHolderAccounts) - 2

    # Remove oldStakeManager and oldFliperDeployer
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
    airdropperRealBalance = newFlipContract.functions.balanceOf(str(airdropper)).call()
    assert airdropperBalance == airdropperRealBalance

    #########################################################
    # TODO: Remove this. This is just for testing purposes (since it could be that someone stakes right away and messes the check)
    newStakeManagerRealBalance = newFlipContract.functions.balanceOf(
        str(newStakeManager)
    ).call()
    assert newStakeManagerRealBalance == int(newStakeManagerBalance)
    #########################################################

    # Do final checking of stakeManager and airdropper balances
    newFlipToBeMinted = oldFliptotalSupply - INIT_SUPPLY
    stakeManagerBalanceDifference = oldStakeManagerBalance - newStakeManagerBalance

    # Check that when updateFlipSupply mints the remaining supply to the StakeManager the balances match.
    # Again, it could be the case where tokens would need to be airdropper to the stakeManager to be burnt, or that some of newSupply
    # tokens that will be minted would have to go to the airdroper, but that won't be the case in this airdrop (and probably never)
    assert newStakeManagerBalance + newFlipToBeMinted == oldStakeManagerBalance
    assert oldFlipDeployerBalance == airdropperBalance


def getAndCheckDeployedAddresses(parsedLog):
    # In the log there should never be more than one set of deployments (either all logged succesfully or none)
    # So we can just use the index of the message string and parse the following lines. Added assertion for safety.
    index = parsedLog.index("New set of contracts deployed")
    # Parse contract addresses
    # Stake Manager
    assert parsedLog[index + 1].split(":")[0] == "StakeManager address", logging.error(
        "Something is wrong in the logging of the deployed StakeManager address"
    )
    newStakeManager = parsedLog[index + 1].split(":")[1]
    assert newStakeManager != ZERO_ADDR, logging.error(
        "Something is wrong with the deployed StakeManager's address"
    )
    # Vault
    assert parsedLog[index + 2].split(":")[0] == "Vault address", logging.error(
        "Something is wrong in the logging of the deployed Vault address"
    )
    newVault = parsedLog[index + 2].split(":")[1]
    assert newVault != ZERO_ADDR, logging.error(
        "Something is wrong with the deployed Vault's address"
    )

    # FLIP
    assert parsedLog[index + 3].split(":")[0] == "FLIP address", logging.error(
        "Something is wrong in the logging of the deployed FLIP address"
    )
    newFlip = parsedLog[index + 3].split(":")[1]
    assert newFlip != ZERO_ADDR, logging.error(
        "Something is wrong with the deployed FLIP's address"
    )

    # Key Manager
    assert parsedLog[index + 4].split(":")[0] == "KeyManager address", logging.error(
        "Something is wrong in the logging of the deployed KeyManager address"
    )
    newKeyManager = parsedLog[index + 4].split(":")[1]
    assert newKeyManager != ZERO_ADDR, logging.error(
        "Something is wrong with the deployed KeyManager's address"
    )

    return (newStakeManager, newVault, newFlip, newKeyManager)
