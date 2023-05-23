import sys
from os import environ, path

sys.path.append(path.abspath("tests"))
from consts import *

from brownie import (
    accounts,
    StateChainGateway,
    FLIP,
    Vault,
    KeyManager,
    MockUSDC,
    web3,
    chain,
    Token,
    network,
)
from brownie.convert import to_address
from brownie.network.event import _decode_logs

import inspect
from datetime import datetime

## TODO: Refactor this to improve this as it creates the airdrop.log file
# from .only_airdrop import fetch_events

FLIP_ADDRESS = environ["FLIP_ADDRESS"]
SC_GATEWAY_ADDRESS = environ["SC_GATEWAY_ADDRESS"]
VAULT_ADDRESS = environ["VAULT_ADDRESS"]

# USDC and KeyManager are optional
USDC_ADDRESS = environ.get("USDC_ADDRESS") or ZERO_ADDR
KEY_MANAGER_ADDRESS = environ.get("KEY_MANAGER_ADDRESS") or ZERO_ADDR


if "SEED" not in environ and network.show_active() != "hardhat":
    userAddress = None
else:
    # Set the priority fee for all transactions
    network.priority_fee("1 gwei")

    if network.show_active() == "hardhat" and "SEED" not in environ:
        AUTONOMY_SEED = "test test test test test test test test test test test junk"
        DEPLOYER_ACCOUNT_INDEX = 0
    else:
        # Live network or hardhat with a seed provided
        AUTONOMY_SEED = environ["SEED"]
        DEPLOYER_ACCOUNT_INDEX = int(environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    userAddress = cf_accs[DEPLOYER_ACCOUNT_INDEX]

    walletAddrs = {}
    seedNumber = 0
    for cf_acc in cf_accs:
        walletAddrs[str(seedNumber)] = cf_acc
        seedNumber += 1


# Define a dictionary of available commands and their corresponding functions
# Tuple order: (function to call, printed help, list of arguments, sendTx bool)
commands = {
    # General commands
    "help": (lambda: help(), "Prints help", [], False),
    "contracts": (lambda: print(contractAddresses), "Prints addresses", [], False),
    "user": (lambda: print(userAddress), "Prints current user address", [], False),
    "walletAddrs": (lambda: print(walletAddrs), "Show wallet addresses", [], False),
    "changeAddr": (
        lambda walletNr: changeAddr(walletNr),
        "Set the user address to that walletAddrs number",
        ["uint256"],
        False,
    ),
    "balanceEth": (
        lambda address: balanceEth(address),
        "Get the Eth balance of an account.",
        ["address"],
        False,
    ),
    "balanceFlip": (
        lambda address: balanceFlip(address),
        "Get the Flip balance of an account",
        ["address"],
        False,
    ),
    "balanceUsdc": (
        lambda address: balanceUsdc(address),
        "Get the USDC balance of an account",
        ["address"],
        False,
    ),
    # "viewTokenTransfersTo": (
    #     lambda address, recipient: viewTokenTransfersTo(address, recipient),
    #     "Display the USDC transfers for an address",
    #     ["address", "address"],
    # ),
    "displaytx": (
        lambda txHash: display_tx(txHash),
        "Display transaction",
        ["bytes32"],
        False,
    ),
    # Transfer tokens
    "transferEth": (
        lambda amount, address: transferEth(amount, address),
        "Transfer Eth to an account. Input should be a float amount in eth",
        ["float", "address"],
        True,
    ),
    "transferFlip": (
        lambda amount, address: transferFlip(amount, address),
        "Transfer Flip to an account.Input float amount up to 18 decimals",
        ["float", "address"],
        True,
    ),
    "transferUsdc": (
        lambda amount, address: transferUsdc(amount, address),
        "Transfer USDC to an account. Input float amount up to 6 decimals",
        ["float", "address"],
        True,
    ),
    # Transactions to State Chain Gateway
    "fund": (
        lambda amount, nodeId: fund(amount, nodeId),
        "Fund account from the user address",
        ["float", "bytes32"],
        True,
    ),
    "executeRedemption": (
        lambda nodeId: executeRedemption(nodeId),
        "Execute an registered redemption",
        ["bytes32"],
        True,
    ),
    # Transactions to Key Manager
    "setAggKeyWGovKey": (
        lambda aggKey: setAggKeyWGovKey(aggKey),
        "Set a new AggKey with the GovKey",
        ["string"],
        True,
    ),
    "setGovKeyWGovKey": (
        lambda address: setGovKeyWGovKey(address),
        "Set a new GovKey with the GovKey",
        ["address"],
        True,
    ),
    "setComKeyWComKey": (
        lambda address: setComKeyWComKey(address),
        "Set a new CommKey with the CommKey",
        ["address"],
        True,
    ),
    # Transactions to Key Manager
    # TODO: Add xSwapNative, xSwapToken, xCallNative, xCallToken
    # View the state of the contracts
    "viewMinFunding": (
        lambda: viewMinFunding(),
        "Display the minimum funding",
        [],
        False,
    ),
    "viewAggKey": (lambda: viewAggKey(), "Display the Aggregate key", [], False),
    "viewGovKey": (lambda: viewGovKey(), "Display the governance address", [], False),
    "viewCommKey": (lambda: viewCommKey(), "Display the community address", [], False),
    "isNonceUsed": (
        lambda nonce: isNonceUsed(nonce),
        "Check if a nonce has been used in the KeyManager",
        ["uint256"],
        False,
    ),
    "viewLastSigTime": (
        lambda: viewLastSigTime(),
        "Display the last time a signature was validated",
        [],
        False,
    ),
    "viewCurrentTime": (
        lambda: viewCurrentTime(),
        "Display the current time (block timestamp)",
        [],
        False,
    ),
    "viewAll": (
        lambda: viewAll(),
        "Display all viewable state variables (to be completed)",
        [],
        False,
    ),
    "exit": (lambda: exit(), "Exits the program", [], False),
}

flip = FLIP.at(f"0x{cleanHexStr(FLIP_ADDRESS)}")
stateChainGateway = StateChainGateway.at(f"0x{cleanHexStr(SC_GATEWAY_ADDRESS)}")
vault = Vault.at(f"0x{cleanHexStr(VAULT_ADDRESS)}")


if KEY_MANAGER_ADDRESS != ZERO_ADDR:
    assert (
        KEY_MANAGER_ADDRESS == vault.getKeyManager()
    ), "KEY_MANAGER_ADDRESS provided doesn't match the contract address that the other contracts point to. Please provide the correct KEY_MANAGER_ADDRESS or remove it from the .env fil"
else:
    KEY_MANAGER_ADDRESS = vault.getKeyManager()

keyManager = KeyManager.at(f"0x{cleanHexStr(KEY_MANAGER_ADDRESS)}")

contractAddresses = {
    "flip": f"0x{cleanHexStr(FLIP_ADDRESS)}",
    "gateway": f"0x{cleanHexStr(SC_GATEWAY_ADDRESS)}",
    "vault": f"0x{cleanHexStr(VAULT_ADDRESS)}",
    "keyManager": f"0x{cleanHexStr(KEY_MANAGER_ADDRESS)}",
}


if USDC_ADDRESS != ZERO_ADDR:
    usdc = MockUSDC.at(f"0x{cleanHexStr(USDC_ADDRESS)}")
    contractAddresses["usdc"] = USDC_ADDRESS


def main():

    print("\n*** Devtool started. Type 'help' for a list of commands ***\n")

    if userAddress == None:
        print("No SEED provided. You can only view the chain\n")

    while True:
        user_input = input("> ")

        # Split the user's input into the command and its arguments
        parts = user_input.split(" ")
        cmd = parts[0]
        args = parts[1:]

        # Check if the command is available
        if cmd in commands:
            # Get the function for the specified command
            func = commands[cmd][0]
            argcount = func.__code__.co_argcount

            if len(args) == argcount == len(commands[cmd][2]):
                i = 0
                while i < argcount:
                    args[i] = checkAndConvertToType(args[i], commands[cmd][2][i])
                    i += 1

                if None in args:
                    print("Argument in position {} is invalid".format(args.index(None)))
                    continue

                if commands[cmd][3]:
                    sendTX = input(
                        "A transaction will be signed and sent. Do you want to proceed? [Y/n]: "
                    )
                    if sendTX not in ["", "y", "Y", "yes", "Yes", "YES"]:
                        continue

                    if userAddress == None:
                        print(
                            "No SEED provided. Please exit and provide a SEED as an env variable."
                        )
                        continue

                # Catch any errors thrown by this logic or by the transaction execution
                try:
                    # Call the function with the arguments
                    func(*args)
                except Exception as e:
                    print(f"Command failed: {e}")
            else:
                print(f"Invalid number of arguments for command {cmd}")
        else:
            print(f"Unknown command: {cmd}")


def help():
    # Print the available commands and their descriptions
    print("\nUsage:  command <arg0> <arg1> ... <argN>")
    print(
        "Note: Contract names can be used as addresses including `user` `vault`, `stateChainGateway` ...\n"
    )

    print("Available commands:\n")
    numCommands = 0
    for name, (func, description, _, _) in commands.items():
        # print("{0:17} {1}".format("  " + name, description))

        print_separators(numCommands)

        params = inspect.getfullargspec(func).args
        argsString = "<" + "> <".join(params) + ">" if len(params) != 0 else ""

        if numCommands == len(commands) - 1:
            # Separate exit from the rest
            print("---------------")
        print("{0:20} {1:28}{2}".format("   " + name, argsString, description))
        numCommands += 1
    print()


# Print separators for the commands - very ugly for now to not waste time on this
def print_separators(numCommands):
    if numCommands == 0:
        print("General Commands\n---------------")
    elif numCommands == 9:
        print("Transfer Tokens\n---------------")
    elif numCommands == 12:
        print("TX to StateChainGateway\n---------------")
    elif numCommands == 14:
        print("TX to KeyManager\n---------------")
    elif numCommands == 17:
        print("View State\n---------------")


def balanceEth(address):
    print(
        "ETH Balance of", str(address), ":", web3.eth.get_balance(str(address)) / E_18
    )


def balanceFlip(a):
    balanceToken("FLIP", flip, a)


def balanceUsdc(a):
    checkUsdcContract()
    balanceToken("USDC", usdc, a)


def balanceToken(tokenName, tokenAddress, address):
    print(
        f"{tokenName} balance of",
        str(address),
        ":",
        tokenAddress.balanceOf(address) / 10 ** (tokenAddress.decimals()),
    )


def transferEth(amount, address):
    tx = userAddress.transfer(address, str(amount) + " ether")
    tx.info()


def transferFlip(amount, address):
    transferToken("FLIP", flip, amount, address)


def transferUsdc(amount, address):
    checkUsdcContract()
    transferToken("USDC", usdc, amount, address)


def checkUsdcContract():
    if "usdc" not in contractAddresses:
        raise Exception(
            "No USDC contract address provided. Please set the USDC_ADDRESS env variable"
        )


def transferToken(tokenName, tokenAddress, amount, address):
    print(f"Sending {amount} {tokenName} to {address}")
    tx = tokenAddress.transfer(
        address,
        amount * 10 ** (tokenAddress.decimals()),
        {"from": userAddress, "required_confs": 1},
    )
    tx.info()


def changeAddr(accountIndex):
    accountIndex = int(accountIndex)
    if accountIndex > 9:
        print("Account index out of range")
        return

    global userAddress
    userAddress = cf_accs[accountIndex]

    print("New user address: ", userAddress)


def fund(amount, node_id):
    amount = float(amount)
    amountInWei = amount * E_18
    if flip.balanceOf(userAddress) < amountInWei:
        print("Insufficient FLIP balance")
        return

    tx = flip.approve(
        stateChainGateway, amountInWei, {"from": userAddress, "required_confs": 1}
    )
    print(f"Approving {amount} FLIP in tx {tx.txid}")

    # Setting required_confs to 1 to ensure we get back the mined tx with all info.
    tx = stateChainGateway.fundStateChainAccount(
        node_id,
        amountInWei,
        {"from": userAddress, "required_confs": 1, "gas_limit": 1000000},
    )
    print(f"Funding {amount} FLIP to node {node_id} in tx {tx.txid}")
    tx.info()


def executeRedemption(nodeId):
    tx = stateChainGateway.executeRedemption(
        nodeId, {"from": userAddress, "required_confs": 1}
    )
    print(f"Executing redemption for node {nodeId} in tx {tx.txid}")
    tx.info()


# Could also input a single aggKey and split them into two in the code (as in deploy.py)
def setAggKeyWGovKey(aggKey):
    aggKey = getKeysFromAggKey(aggKey)
    tx = keyManager.setAggKeyWithGovKey(
        aggKey, {"from": userAddress, "required_confs": 1}
    )
    tx.info()


def setGovKeyWGovKey(newGovKey):
    tx = keyManager.setGovKeyWithGovKey(
        newGovKey, {"from": userAddress, "required_confs": 1}
    )
    tx.info()


def setComKeyWComKey(newComKey):
    tx = keyManager.setCommKeyWithCommKey(
        newComKey, {"from": userAddress, "required_confs": 1}
    )
    tx.info()


def viewPendRedemption(nodeId):
    redemption = stateChainGateway.getPendingRedemption(nodeId)
    if redemption == [0, ZERO_ADDR, 0, 0]:
        print(f"No pending redemption for node {nodeId}")
    else:
        print(
            f"Redemption with for node {nodeId} with amount {redemption[0]}, funder {redemption[1]}, startTime {redemption[2]}, expiryTime {redemption[3]}"
        )


def viewMinFunding():
    minFunding = stateChainGateway.getMinimumFunding()
    print(f"Min funding: {minFunding / 10 ** (flip.decimals())} FLIP ")


def viewAggKey():
    aggKey = keyManager.getAggregateKey()
    print(f"Aggregate key: {aggKey}")


def viewGovKey():
    governor = vault.getGovernor()
    print(f"Governor address: {governor}")


def viewCommKey():
    communityKey = vault.getCommunityKey()
    print(f"Community Address: {communityKey}")


def isNonceUsed(nonce):
    used = keyManager.isNonceUsedByAggKey(nonce)
    if used:
        print(f"Nonce {nonce} has been used")
    else:
        print(f"Nonce {nonce} has not been used")


def viewLastSigTime():
    lastTime = keyManager.getLastValidateTime()
    print(f"Last time a signature was validated: {lastTime}")
    printUserReadableTime(lastTime)


def viewCurrentTime():
    timestamp = chain.time()
    print(f"Current time: {timestamp}")
    printUserReadableTime(timestamp)


def printUserReadableTime(timestamp):
    print(f"User readable time: {datetime.fromtimestamp(timestamp)}")


def viewAll():
    viewMinFunding()
    viewAggKey()
    viewGovKey()
    viewCommKey()
    viewLastSigTime()
    viewCurrentTime()


# TODO: Add swapNative and swapToken through the Vault.


# TODO: Rewrite this so it is useful - we cannot fetch all events in history,
# caps at 1000 events, and also it's not parsable by the user.
# def viewAllTokenTransfers(address, initial_block=0):
#     contractObject = getERC20ContractFromAddress(address)

#     events = list(
#         fetch_events(
#             contractObject.events.Transfer,
#             from_block=initial_block,
#             to_block=web3.eth.block_number,
#         )
#     )
#     return events


# def viewTokenTransfersTo(tokenAddress, recipient):
#     transferEvents = viewAllTokenTransfers(tokenAddress)

#     # listEvents = []
#     for event in transferEvents:
#         if event.args.to == recipient:
#             print(event)
#             # listEvents.append(event)


# def getERC20ContractFromAddress(address):
#     abi = ""
#     if address == FLIP_ADDRESS:
#         abi = "build/contracts/FLIP.json"
#     elif address == USDC_ADDRESS:
#         abi = "build/contracts/MockUSDC.json"
#     else:
#         abi = "build/contracts/Token.json"

#     with open(abi) as f:
#         info_json = json.load(f)
#     abi = info_json["abi"]

#     # Object to get the event interface from
#     tokenContractObject = web3.eth.contract(address=address, abi=abi)

#     return tokenContractObject


# We can't display it the same way as for a brownie-broadcasted transaction (tx.info()).
def display_tx(txHash):

    try:
        receipt = web3.eth.get_transaction_receipt(txHash)
    except:
        print("Error getting transaction receipt")
        return

    print("--------- Raw transaction receipt -----------")
    print(receipt)
    print("--------- Events log -----------")
    decodedLogs = _decode_logs(receipt.logs)
    for eventName, values in decodedLogs.items():
        # Print each key-value pair in the format "key: item"
        print("{}: {}".format(eventName, values))


def getAddress(a):
    # Check if the input is an alias for an addresss
    if a in contractAddresses:
        return contractAddresses[a]
    elif a == "user":
        return userAddress
    else:
        # Check if the input is a valid Ethereum address
        try:
            # print("Valid Ethereum address")
            # Try to create an Account object from the user input
            return to_address(a)
        except ValueError:
            # If the user input is not a valid Ethereum address, print a message
            print("Invalid Ethereum address")
            return None


def checkAndConvertToType(input, type):
    if type == "uint256":
        if input.isdigit():
            number = int(input)
            if number >= 0 and number <= 2**256 - 1:
                return number
        else:
            print("Invalid type - introduce an integer")
    if type == "uint8":
        if input.isdigit():
            number = int(input)
            if number >= 0 and number <= 2**8 - 1:
                return number
        else:
            print("Invalid type - introduce a uint8")
    elif type == "float":
        try:
            number = float(input)
            if number >= 0 and number <= 2**256 - 1:
                return float(input)
        except ValueError:
            print("Invalid type - introduce an float")
    elif type == "address":
        return getAddress(input)
    elif type == "string":
        return input
    elif type == "bytes32":
        return input

    return None
