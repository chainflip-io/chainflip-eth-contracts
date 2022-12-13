import sys
from os import environ, path

sys.path.append(path.abspath("tests"))
from consts import *

from brownie import accounts, StakeManager, FLIP, chain, web3

# TODO: To add other contracts? At least USDC.
FLIP_ADDRESS = environ["FLIP_ADDRESS"]
STAKE_MANAGER_ADDRESS = environ["STAKE_MANAGER_ADDRESS"]
VAULT_ADDRESS = environ["STAKE_MANAGER_ADDRESS"]


AUTONOMY_SEED = environ["SEED"]
DEPLOYER_ACCOUNT_INDEX = int(environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
userAddress = cf_accs[DEPLOYER_ACCOUNT_INDEX]

# stake = 10**3 * E_18
# return_addr = "0xffffffffffffffffffffffffffffffffffffffff"

# Define a dictionary of available commands and their corresponding functions
commands = {
    "help": (lambda: help(), "Prints help"),
    "hello": (lambda: print("Hello, world!"), "Prints 'Hello, world!'"),
    "balance": (
        lambda a: balance(a),
        "Get the balance of an account.",
    ),
    "balanceFlip": (lambda a: balanceFlip(a), "Get the balance of an account"),
    "contracts": (lambda: print(contractAddresses), "Prints addresses"),
    "user": (lambda: print(userAddress), "Prints current user address"),
    "walletAddresses": (lambda: print(walletAddresses), "Show wallet addresses"),
    "changeAddress": (lambda i: changeAddress(i), "Change selected address"),
    "stake": (lambda a, b: stake(a, b), "Stake flip from the user address"),
    "exit": (lambda: exit(), "Exits the program"),
}

contractAddresses = {
    "flip": FLIP_ADDRESS,
    "stakeManager": STAKE_MANAGER_ADDRESS,
    "vault": VAULT_ADDRESS,
}

walletAddresses = {}
seedNumber = 1
for cf_acc in cf_accs:
    walletAddresses[str(seedNumber)] = cf_acc
    seedNumber += 1

# The same thing is already under tests/utils.py
# def cleanHexStr(thing):
#     if isinstance(thing, int):
#         thing = hex(thing)
#     elif not isinstance(thing, str):
#         thing = thing.hex()
#     return thing[2:] if thing[:2] == "0x" else thing

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

            if len(args) == argcount:
                # Call the function with the arguments
                func(*args)
            else:
                print(f"Invalid number of arguments for command {cmd}")
        else:
            print(f"Unknown command: {cmd}")


def help():
    # Print the available commands and their descriptions
    print("\nUsage:  command <arg0> <arg1> ... <argN>\n")
    print("Available commands:")
    for name, (func, description) in commands.items():
        print("{0:17} {1}".format("  " + name, description))
        # TODO: Add argument list and description to help.
        argcount = func.__code__.co_argcount
        # print(" argcount: ", argcount)


def balance(a):
    address = getAddress(a)
    print("ETH Balance of", a, ":", web3.eth.get_balance(str(address)) / E_18)


def balanceFlip(a):
    balanceToken("FLIP", flip, a)


def balanceToken(tokenName, tokenAddress, a):
    address = getAddress(a)
    print(
        f"{tokenName} balance of",
        address,
        ":",
        tokenAddress.balanceOf(address) / 10 ** (tokenAddress.decimals()),
    )


def changeAddress(accountIndex):
    accountIndex = int(accountIndex)
    if accountIndex > 9:
        print("Account index out of range")
        return

    global userAddress
    userAddress = cf_accs[accountIndex]

    print("New user address: ", userAddress)


def stake(amount, node_id):
    amountInWei = amount * E_18
    if flip.balanceOf(userAddress) < amountInWei:
        print("Insufficient FLIP balance")
        return

    tx = flip.approve(
        stakeManager, amountInWei, {"from": userAddress, "required_confs": 1}
    )
    print(f"Approving {amount} FLIP in tx {tx.txid}")

    node_id = node_id.strip()
    tx = stakeManager.stake(
        node_id,
        amountInWei,
        userAddress,
        {"from": userAddress, "required_confs": 0, "gas_limit": 1000000},
    )
    print(f"Staking {amount} FLIP to node {node_id} in tx {tx.txid}")


def getAddress(a):
    # Check if the input is an alias for an addresss
    if a in contractAddresses:
        return contractAddresses[a]
    elif a == "user":
        return userAddress
    else:
        # TODO: Check that this is a valid address, otherwise handle the error
        return a
