import sys
from os import environ, path

sys.path.append(path.abspath("tests"))
from consts import *

from brownie import (
    accounts,
    StakeManager,
    FLIP,
    Vault,
    KeyManager,
    MockUSDC,
    web3,
    chain,
)
from brownie.convert import to_address
from brownie.network.event import _decode_logs

import inspect

FLIP_ADDRESS = environ["FLIP_ADDRESS"]
STAKE_MANAGER_ADDRESS = environ["STAKE_MANAGER_ADDRESS"]
VAULT_ADDRESS = environ["VAULT_ADDRESS"]

# USDC and KeyManager are optional
USDC_ADDRESS = environ.get("USDC_ADDRESS") or ZERO_ADDR
KEY_MANAGER_ADDRESS = environ.get("KEY_MANAGER_ADDRESS") or ZERO_ADDR


AUTONOMY_SEED = environ["SEED"]
DEPLOYER_ACCOUNT_INDEX = int(environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
userAddress = cf_accs[DEPLOYER_ACCOUNT_INDEX]


# Define a dictionary of available commands and their corresponding functions

commands = {
    "help": (lambda: help(), "Prints help", []),
    "contracts": (lambda: print(contractAddresses), "Prints addresses", []),
    "user": (lambda: print(userAddress), "Prints current user address", []),
    "walletAddrs": (lambda: print(walletAddrs), "Show wallet addresses", []),
    "changeAddr": (
        lambda walletNr: changeAddr(walletNr),
        "Sete the user address to that walletAddrs number",
        ["uint256"],
    ),
    "balanceEth": (
        lambda address: balanceEth(address),
        "Get the Eth balance of an account.",
        ["address"],
    ),
    "balanceFlip": (
        lambda address: balanceFlip(address),
        "Get the Flip balance of an account",
        ["address"],
    ),
    "balanceUsdc": (
        lambda address: balanceUsdc(address),
        "Get the USDC balance of an account",
        ["address"],
    ),
    "transferEth": (
        lambda amount, address: transferEth(amount, address),
        "Transfer Eth to an account. Input should be a float amount in eth`",
        ["float", "address"],
    ),
    "transferFlip": (
        lambda amount, address: transferFlip(amount, address),
        "Transfer Flip to an account.Input float amount up to 18 decimals",
        ["float", "address"],
    ),
    "transferUsdc": (
        lambda amount, address: transferUsdc(amount, address),
        "Transfer USDC to an account. Input float amount up to 6 decimals",
        ["float", "address"],
    ),
    "stake": (
        lambda amount, nodeId: stake(amount, nodeId),
        "Stake flip from the user address",
        ["float", "bytes32"],
    ),
    "executeClaim": (
        lambda nodeId: executeClaim(nodeId),
        "Execute an registered claim",
        ["bytes32"],
    ),
    "enableSwaps": (
        lambda: enableVaultSwaps(),
        "Enable Vault swaps. User needs to be the governance address",
        [],
    ),
    "disableSwaps": (
        lambda: disableVaultSwaps(),
        "Disable Vault swaps. User needs to be the governance address",
        [],
    ),
    "viewMinStake": (
        lambda: viewMinStake(),
        "Display the minimum stake",
        [],
    ),
    "viewAggKey": (
        lambda: viewAggKey(),
        "Display the Aggregate key",
        [],
    ),
    "viewGovKey": (
        lambda: viewGovKey(),
        "Display the governance address",
        [],
    ),
    "viewCommKey": (
        lambda: viewCommKey(),
        "Display the community address",
        [],
    ),
    "isNonceUsed": (
        lambda nonce: isNonceUsed(nonce),
        "Check if the nonce has been used",
        ["uint256"],
    ),
    "viewLastTime": (
        lambda: viewLastTime(),
        "Display the last time a signature was validated",
        [],
    ),
    "viewCurrentTime": (
        lambda: viewCurrentTime(),
        "Display the current time (block timestamp)",
        [],
    ),
    "displaytx": (
        lambda txHash: display_tx(txHash),
        "Display transaction",
        ["bytes32"],
    ),
    "exit": (lambda: exit(), "Exits the program", []),
}

contractAddresses = {
    "flip": FLIP_ADDRESS,
    "stakeManager": STAKE_MANAGER_ADDRESS,
    "vault": VAULT_ADDRESS,
}

walletAddrs = {}
seedNumber = 0
for cf_acc in cf_accs:
    walletAddrs[str(seedNumber)] = cf_acc
    seedNumber += 1

flip = FLIP.at(f"0x{cleanHexStr(FLIP_ADDRESS)}")
stakeManager = StakeManager.at(f"0x{cleanHexStr(STAKE_MANAGER_ADDRESS)}")
vault = Vault.at(f"0x{cleanHexStr(VAULT_ADDRESS)}")
if KEY_MANAGER_ADDRESS != ZERO_ADDR:
    keyManager = KeyManager.at(f"0x{cleanHexStr(KEY_MANAGER_ADDRESS)}")
    contractAddresses["keyManager"] = KEY_MANAGER_ADDRESS
if USDC_ADDRESS != ZERO_ADDR:
    usdc = MockUSDC.at(f"0x{cleanHexStr(USDC_ADDRESS)}")
    contractAddresses["usdc"] = USDC_ADDRESS


def main():

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
    print("\nUsage:  command <arg0> <arg1> ... <argN>\n")
    print("Available commands:")
    for name, (func, description, _) in commands.items():
        # print("{0:17} {1}".format("  " + name, description))

        params = inspect.getfullargspec(func).args
        argsString = "<" + "> <".join(params) + ">" if len(params) != 0 else ""

        print("{0:18} {1:21}{2}".format("   " + name, argsString, description))


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


def checkKeyManagerContract():
    if "keyManager" not in contractAddresses:
        raise Exception(
            "No KeyManager contract address provided. Please set the KEY_MANAGER_ADDRESS env variable"
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


def stake(amount, node_id):
    amount = float(amount)
    amountInWei = amount * E_18
    if flip.balanceOf(userAddress) < amountInWei:
        print("Insufficient FLIP balance")
        return

    tx = flip.approve(
        stakeManager, amountInWei, {"from": userAddress, "required_confs": 1}
    )
    print(f"Approving {amount} FLIP in tx {tx.txid}")

    # Setting required_confs to 1 to ensure we get back the mined tx with all info.
    tx = stakeManager.stake(
        node_id,
        amountInWei,
        userAddress,
        {"from": userAddress, "required_confs": 1, "gas_limit": 1000000},
    )
    print(f"Staking {amount} FLIP to node {node_id} in tx {tx.txid}")
    tx.info()


def executeClaim(nodeId):
    tx = stakeManager.executeClaim(nodeId, {"from": userAddress, "required_confs": 1})
    print(f"Executing claim for node {nodeId} in tx {tx.txid}")
    tx.info()


def viewPendClaim(nodeId):
    claim = stakeManager.getPendingClaim(nodeId)
    if claim == [0, ZERO_ADDR, 0, 0]:
        print(f"No pending claim for node {nodeId}")
    else:
        print(
            f"Claim with for node {nodeId} with amount {claim[0]}, staker {claim[1]}, startTime {claim[2]}, expiryTime {claim[3]}"
        )


def viewMinStake():
    minStake = stakeManager.getMinimumStake()
    print(f"Min stake: {minStake / 10 ** (flip.decimals())} FLIP ")


def viewAggKey():
    checkKeyManagerContract()
    aggKey = keyManager.getAggregateKey()
    print(f"Aggregate key: {aggKey}")


def viewGovKey():
    governor = vault.getGovernor()
    print(f"Governor address: {governor}")


def viewCommKey():
    communityKey = vault.getCommunityKey()
    print(f"Community Address: {communityKey}")


def isNonceUsed(nonce):
    checkKeyManagerContract()
    used = keyManager.isNonceUsedByAggKey(nonce)
    if used:
        print(f"Nonce {nonce} has been used")
    else:
        print(f"Nonce {nonce} has not been used")


def viewLastTime():
    checkKeyManagerContract()
    lastTime = keyManager.getLastValidateTime()
    print(f"Last time: {lastTime}")


def viewCurrentTime():
    print(f"Current time: {chain.time()}")


# TODO: Add swapNative and swapToken through the Vault.
# TODO: enableSwaps will need to be renamed to enablexCalls
def enableVaultSwaps():
    tx = vault.enableSwaps({"from": userAddress, "required_confs": 1})
    tx.info()
    print(">> Vault swaps enabled succesfully <<")


def disableVaultSwaps():
    tx = vault.disableSwaps({"from": userAddress, "required_confs": 1})
    tx.info()
    print(">> Vault swaps disabled succesfully <<")


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
