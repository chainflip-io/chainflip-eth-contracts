import sys
from os import environ, path

sys.path.append(path.abspath("tests"))
from consts import *

from brownie import accounts, StakeManager, FLIP, chain, web3

# TODO: To add other contracts
FLIP_ADDRESS = environ["FLIP_ADDRESS"]
STAKE_MANAGER_ADDRESS = environ["STAKE_MANAGER_ADDRESS"]


AUTONOMY_SEED = environ["SEED"]
DEPLOYER_ACCOUNT_INDEX = int(environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
userAddress = cf_accs[DEPLOYER_ACCOUNT_INDEX]

flip = FLIP.at(FLIP_ADDRESS)

# stake = 10**3 * E_18
#return_addr = "0xffffffffffffffffffffffffffffffffffffffff"

# Define a dictionary of available commands and their corresponding functions
commands = {
    "help": (lambda: help(), "Prints help"),
    "hello": (lambda: print("Hello, world!"), "Prints 'Hello, world!'"),
    "balance": (lambda a: balance(a), "Get the balance of an account",),
    "balanceFlip": (lambda a: balanceFlip(a), "Get the balance of an account",),
    "contracts": (lambda: print(contractAddresses), "Prints addresses"),
    "user": (lambda: print(userAddress), "Prints current user address"),
    "walletAddresses": (lambda : print(walletAddresses), "Show wallet addresses"),
    "changeAddress": (lambda i: changeAddress(i), "Change selected address"),
    #"add": (lambda x, y: print(x + y), "Adds two numbers together"),
    "exit": (lambda: exit(), "Exits the program")
}

contractAddresses = {
    "flip": FLIP_ADDRESS,
    "stakeManager": STAKE_MANAGER_ADDRESS,
}

walletAddresses = {}
seedNumber = 1
for cf_acc in cf_accs:
    walletAddresses[str(seedNumber)] = cf_acc
    seedNumber += 1

def main():
    flip = FLIP.at(f"0x{cleanHexStr(FLIP_ADDRESS)}")
    # stakeManager = StakeManager.at(f"0x{cleanHexStr(STAKE_MANAGER_ADDRESS)}")
    # sender = cf_accs[DEPLOYER_ACCOUNT_INDEX]



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
    for name,(func, description) in commands.items():
        print("{0:17} {1}".format("  "+name, description))
        # TODO: Add argument list and description to help.
        argcount = func.__code__.co_argcount
        #print(" argcount: ", argcount)


def balance(a):
    print("ETH Balance of", a, ":", web3.eth.get_balance(a))

def balanceFlip(a):
    global flip
    print("FLIP Balance of", a, ":", flip.balanceOf(a))

def changeAddress(accountIndex):
    accountIndex = int(accountIndex)
    if accountIndex > 9:
        print("Account index out of range")
        return

    global userAddress 
    userAddress = cf_accs[accountIndex]

    print("New user address: ", userAddress)


# def stake():
#     to_approve = flip.balanceOf(staker)
#     tx = flip.approve(stakeManager, to_approve, {"from": staker, "required_confs": 1})
#     print(f"Approving {to_approve / E_18} FLIP in tx {tx.txid}")
#     for i, node_id in enumerate(node_ids):
#         to_stake = stake + (i * E_18)
#         node_id = node_id.strip()
#         tx = stakeManager.stake(
#             node_id,
#             to_stake,
#             return_addr,
#             {"from": staker, "required_confs": 0, "gas_limit": 1000000},
#         )
#         print(f"Staking {to_stake / E_18} FLIP to node {node_id} in tx {tx.txid}")

# def help():
#     print("Available commands:")
#     for cmd in commands:
#         print(f"- {cmd}")

def cleanHexStr(thing):
    if isinstance(thing, int):
        thing = hex(thing)
    elif not isinstance(thing, str):
        thing = thing.hex()
    return thing[2:] if thing[:2] == "0x" else thing
