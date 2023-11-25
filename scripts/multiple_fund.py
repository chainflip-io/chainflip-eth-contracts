import sys
from os import environ, path

sys.path.append(path.abspath("tests"))
from consts import *
from utils import prompt_user_continue_or_break
from brownie import accounts, StateChainGateway, FLIP, network


###
# NODE_ID_FILE should be formatted as a list of "NODE_IDs,amount" separated by a newline. AMOUNT must be without the decimals.
# E.g. to fund 4 and 5 FLIP to two nodes:
# 0xa4617d287f441d8b0c3fce42271b42826581359c309bcb2d1fb17ed3d20f9022,4
# 0x000015090e14ef2bc1be23bb39eb06bc904150a2ba5bde8cc9a12dc35530f412,5
###

FLIP_ADDRESS = environ["FLIP_ADDRESS"] # 0x826180541412D574cf1336d22c0C0a287822678A" for mainnet FLIP
SC_GATEWAY_ADDRESS = environ["SC_GATEWAY_ADDRESS"] # 0x6995Ab7c4D7F4B03f467Cf4c8E920427d9621DBd for mainnet
AUTONOMY_SEED = environ["SEED"]

# NODE_ID_FILE to read from
NODE_ID_FILE = environ["NODE_ID_FILE"]

DEPLOYER_ACCOUNT_INDEX = int(environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
network.priority_fee("0.1 gwei")

def main():
    flip = FLIP.at(f"0x{cleanHexStr(FLIP_ADDRESS)}")
    stateChainGateway = StateChainGateway.at(f"0x{cleanHexStr(SC_GATEWAY_ADDRESS)}")
    funder = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    print(f"Funder account: {funder}")

    with open(NODE_ID_FILE, "r") as f:
        lines = f.readlines()

    to_approve = 0
    number_of_nodes = 0
    nodes = []
    for line in lines:
        node_id, amount = line.strip().split(',')
        to_approve += int(amount)
        number_of_nodes += 1
        print(f"To fund {amount} FLIP for node {node_id}")
        assert node_id not in nodes, f"Duplicate node id {node_id}"
        nodes.append(node_id)

    balance_deployer = flip.balanceOf(funder)
    print(f"Funder initial FLIP balance {balance_deployer//E_18}")
    assert balance_deployer >= to_approve * E_18, f"Insufficient balance to fund {to_approve} FLIP, only {balance_deployer / E_18} FLIP available"

    prompt_user_continue_or_break(f"Approving to {number_of_nodes} nodes for a total amount of {to_approve} FLIP", True)

    flip.approve(
        stateChainGateway, to_approve * E_18, {"from": funder, "required_confs": 1}
    )
    print(f"Approved {to_approve} FLIP")

    prompt_user_continue_or_break(f"Funding accounts", True)

    for line in lines:
        node_id, amount = line.strip().split(',')
        to_fund = int(amount)  * E_18
        node_id = node_id.strip()
        print(f"Funding {to_fund / E_18} FLIP to node {node_id}")
        tx = stateChainGateway.fundStateChainAccount(
            node_id,
            to_fund,
            {"from": funder, "required_confs": 1},
        )
        tx.info()

    print(f"Funder final FLIP balance {flip.balanceOf(funder)//E_18}")


def cleanHexStr(thing):
    if isinstance(thing, int):
        thing = hex(thing)
    elif not isinstance(thing, str):
        thing = thing.hex()
    return thing[2:] if thing[:2] == "0x" else thing
