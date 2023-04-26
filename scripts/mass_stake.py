import sys
from os import environ, path

sys.path.append(path.abspath("tests"))
from consts import *

from brownie import accounts, StateChainGateway, FLIP

FLIP_ADDRESS = environ["FLIP_ADDRESS"]
GATEWAY_ADDRESS = environ["GATEWAY_ADDRESS"]
AUTONOMY_SEED = environ["SEED"]

# File should be formatted as a list of NODE_IDs separated by a newline
NODE_ID_FILE = environ["NODE_ID_FILE"]

DEPLOYER_ACCOUNT_INDEX = int(environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)

node_ids = []

stake = 10**3 * E_18
return_addr = "0xffffffffffffffffffffffffffffffffffffffff"


def main():
    flip = FLIP.at(f"0x{cleanHexStr(FLIP_ADDRESS)}")
    stateChainGateway = StateChainGateway.at(f"0x{cleanHexStr(GATEWAY_ADDRESS)}")
    with open(NODE_ID_FILE, "r") as f:
        node_ids = f.readlines()
        f.close()
    funder = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    to_approve = flip.balanceOf(funder)
    tx = flip.approve(
        stateChainGateway, to_approve, {"from": funder, "required_confs": 1}
    )
    print(f"Approving {to_approve / E_18} FLIP in tx {tx.txid}")
    for i, node_id in enumerate(node_ids):
        to_stake = stake + (i * E_18)
        node_id = node_id.strip()
        tx = stateChainGateway.stake(
            node_id,
            to_stake,
            return_addr,
            {"from": funder, "required_confs": 0, "gas_limit": 1000000},
        )
        print(f"Staking {to_stake / E_18} FLIP to node {node_id} in tx {tx.txid}")


def cleanHexStr(thing):
    if isinstance(thing, int):
        thing = hex(thing)
    elif not isinstance(thing, str):
        thing = thing.hex()
    return thing[2:] if thing[:2] == "0x" else thing
