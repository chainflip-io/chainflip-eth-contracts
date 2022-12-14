import sys
from os import environ, path

sys.path.append(path.abspath("tests"))
from consts import *

from brownie import accounts, StakeManager, FLIP, chain, web3
from brownie.convert import to_address
from brownie.network.event import _decode_logs

import inspect

# TODO: To add other contracts? At least USDC.
FLIP_ADDRESS = environ["FLIP_ADDRESS"]
STAKE_MANAGER_ADDRESS = environ["STAKE_MANAGER_ADDRESS"]
VAULT_ADDRESS = environ["STAKE_MANAGER_ADDRESS"]


AUTONOMY_SEED = environ["SEED"]
DEPLOYER_ACCOUNT_INDEX = int(environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
userAddress = cf_accs[DEPLOYER_ACCOUNT_INDEX]


# Define a dictionary of available commands and their corresponding functions
commands = {
    "help": (lambda: help(), "Prints help", []),
    "balance": (
        lambda address: balance(address),
        "Get the balance of an account.",
        ["address"],
    ),
    "balanceFlip": (
        lambda address: balanceFlip(address),
        "Get the balance of an account",
        ["address"],
    ),
    "contracts": (lambda: print(contractAddresses), "Prints addresses", []),
    "user": (lambda: print(userAddress), "Prints current user address", []),
    "walletAddrs": (lambda: print(walletAddrs), "Show wallet addresses", []),
    "changeAddr": (
        lambda walletNr: changeAddr(walletNr),
        "Change selected address",
        ["int"],
    ),
    "stake": (
        lambda flipAmount, nodeId: stake(flipAmount, nodeId),
        "Stake flip from the user address",
        ["int", "int"],
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
seedNumber = 1
for cf_acc in cf_accs:
    walletAddrs[str(seedNumber)] = cf_acc
    seedNumber += 1

flip = FLIP.at(f"0x{cleanHexStr(FLIP_ADDRESS)}")
stakeManager = StakeManager.at(f"0x{cleanHexStr(STAKE_MANAGER_ADDRESS)}")


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
                    args[i] = convertToType(args[i], commands[cmd][2][i])
                    i += 1

                if None in args:
                    print("Argument in position {} is invalid".format(args.index(None)))
                    continue

                # TODO: We can have a try-catch hjere to ensure we never crash the tool.
                # We don't have it for development to be able to see the errors.
                func(*args)

                # Try except to catch any unexpected errors
                # try:
                #     # Call the function with the arguments
                #     func(*args)
                # except:
                #     print("Error executing command")
            else:
                print(f"Invalid number of arguments for command {cmd}")
        else:
            print(f"Unknown command: {cmd}")


def help():
    # Print the available commands and their descriptions
    print("\nUsage:  command <arg0> <arg1> ... <argN>\n")
    print("Available commands:")
    for name, (func, description, argsType) in commands.items():
        # print("{0:17} {1}".format("  " + name, description))

        params = inspect.getfullargspec(func).args
        argsString = "<" + "> <".join(params) + ">" if len(params) != 0 else ""

        print("{0:14} {1:23}{2}".format("  " + name, argsString, description))


def balance(address):
    print(
        "ETH Balance of", str(address), ":", web3.eth.get_balance(str(address)) / E_18
    )


def balanceFlip(a):
    balanceToken("FLIP", flip, a)


def balanceToken(tokenName, tokenAddress, address):
    print(
        f"{tokenName} balance of",
        str(address),
        ":",
        tokenAddress.balanceOf(address) / 10 ** (tokenAddress.decimals()),
    )


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
    print(_decode_logs(receipt.logs))


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


def convertToType(input, type):
    if type == "int":
        if input.isdigit():
            return int(input)
        else:
            print("Invalid type - introduce an integer")
    elif type == "float":
        try:
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
