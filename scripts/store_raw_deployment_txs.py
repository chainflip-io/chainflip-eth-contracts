import sys
import os
import json

sys.path.append(os.path.abspath("tests"))
from consts import *

from brownie import network,web3, accounts

AUTONOMY_SEED = os.environ["SEED"]
DEPLOY_RAW_TX_ID = os.environ["DEPLOY_RAW_TX_ID"]
cf_accs = accounts.from_mnemonic(os.environ["SEED"], count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)
deployer = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {deployer}")

def main():
    latest_block = web3.eth.block_number
    raw_transactions = []

    # Iterate over all blocks
    for blockNumber in range(0, latest_block):
        # Get the block details
        block = web3.eth.get_block(blockNumber+1)

        # Extract and print the transactions
        transactions = block['transactions']

        for tx in transactions:
            tx_data = web3.eth.get_transaction(tx.hex())
            sender = tx_data['from']
            if sender == deployer:
                raw_transactions.append(web3.eth.get_raw_transaction(tx.hex()).hex())

    data = {i: hex_string for i, hex_string in enumerate(raw_transactions)}

    dir_path = os.path.dirname(os.path.abspath(__file__)) + "/.artefacts"
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    # Open a new JSON file in write mode
    with open(f"{dir_path}/{DEPLOY_RAW_TX_ID}.json", "w") as f:
        json.dump(data, f)


def send_raw_json_txs():
    dir_path = os.path.dirname(os.path.abspath(__file__)) + "/.artefacts"

    # Open the JSON file and read its contents
    with open(f"{dir_path}/{DEPLOY_RAW_TX_ID}.json", "r") as f:
        data = json.load(f)

    # Loop through each raw transaction data
    for raw_tx in data.values():
        # Send the raw transaction
        tx_hash = web3.eth.sendRawTransaction(raw_tx)
        print(f'Transaction sent with hash: {tx_hash.hex()}')

def get_number_txs():
    print(web3.eth.get_transaction_count(deployer))