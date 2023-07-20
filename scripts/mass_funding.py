import sys
from os import environ, path

sys.path.append(path.abspath("tests"))
from consts import *

from brownie import accounts, StateChainGateway, FLIP

FLIP_ADDRESS = environ["FLIP_ADDRESS"]
SC_GATEWAY_ADDRESS = environ["SC_GATEWAY_ADDRESS"]
AUTONOMY_SEED = environ["SEED"]
FLIP_AMOUNT = int(environ.get("FLIP_AMOUNT", int(10**3)))

# File should be formatted as a list of NODE_IDs separated by a newline
NODE_ID_FILE = environ["NODE_ID_FILE"]

DEPLOYER_ACCOUNT_INDEX = int(environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)

node_ids = []

funding_amount = FLIP_AMOUNT * E_18


def main():
    flip = FLIP.at(f"0x{cleanHexStr(FLIP_ADDRESS)}")
    stateChainGateway = StateChainGateway.at(f"0x{cleanHexStr(SC_GATEWAY_ADDRESS)}")
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
        to_fund = funding_amount + (i * E_18)
        node_id = node_id.strip()
        tx = stateChainGateway.fundStateChainAccount(
            node_id,
            to_fund,
            {"from": funder, "required_confs": 0, "gas_limit": 1000000},
        )
        print(f"Funding {to_fund / E_18} FLIP to node {node_id} in tx {tx.txid}")


def cleanHexStr(thing):
    if isinstance(thing, int):
        thing = hex(thing)
    elif not isinstance(thing, str):
        thing = thing.hex()
    return thing[2:] if thing[:2] == "0x" else thing
