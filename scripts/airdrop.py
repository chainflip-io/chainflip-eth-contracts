import sys
import os
import csv
import time

sys.path.append(os.path.abspath("tests"))
from consts import *
from deploy import (
    transaction_params,
)
from utils import prompt_user_continue_or_break
from brownie import (
    project,
    chain,
    accounts,
    FLIP,
    network,
    web3,
)
from datetime import datetime

_project = project.get_loaded_projects()[0]
IAirdropContract = _project.interface.IAirdrop
address_wenTokens = "0x2c952eE289BbDB3aEbA329a4c41AE4C836bcc231"

# File should be formatted as a list of parameters. First line should be the headers with names of the
# parameters. The rest of the lines should be the values for each parameter. It should contain the
# parameters described in the order dictionary below but it can have others, which will be ignored.
AIRDROP_INFO_FILE = os.environ["AIRDROP_INFO_FILE"]
columns = [
    "Full name/Company Name",
    "Email Address",
    "Final Choice Lock up Schedule",
    "Investor Label",
    "# tokens",
    "Beneficiary Wallet Address",
    "Address transfer enabled in smart contract?",
    "Yeet Function?",
    "Sanity checked?",
]

AUTONOMY_SEED = os.environ["SEED"]
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]

print(f"DEPLOYER = {DEPLOYER}")
transaction_params()


def main():
    if chain.id == 1:
        prompt_user_continue_or_break(
            "\n[WARNING] You are about to interact with Ethereum mainnet",
            False,
        )

    flip_address = os.environ[
        "FLIP_ADDRESS"
    ]  # 0x826180541412D574cf1336d22c0C0a287822678A" for mainnet FLIP

    flip = FLIP.at(f"0x{cleanHexStr(flip_address)}")

    recipient_to_amount_E18 = {}
    flip_total_E18 = 0
    total_rows = 0

    assert os.path.isfile(AIRDROP_INFO_FILE), f"File {AIRDROP_INFO_FILE} not found"

    prompt_user_continue_or_break("Parsing airdrop file", True)

    with open(AIRDROP_INFO_FILE, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')

        # Check the first row - parameter names
        first_row = next(reader)
        for position, parameter_name in enumerate(columns):
            assert (
                first_row[position] == parameter_name
            ), f"Incorrect parameter name: expected {parameter_name}, but got {first_row[position]}"

        # Read the rest of the rows
        for row in reader:
            assert len(row) == len(
                columns
            ), f"Incorrect number of parameters: expected {len(columns)}, but got {len(row)}"

            # Check beneficiary
            beneficiary = row[columns.index("Beneficiary Wallet Address")]

            if beneficiary == "":
                print(f"Skipping row with no beneficiary {row}")
                continue

            assert web3.isAddress(
                beneficiary
            ), f"Incorrect beneficiary address {beneficiary}, {row}"

            # Check lockup type
            lockup_type = row[columns.index("Final Choice Lock up Schedule")]

            # Should only accept "Airdrop"
            if lockup_type != "Airdrop":
                raise Exception(f"Incorrect lockup type parameter {lockup_type}")

            # Check amount
            amount = row[columns.index("# tokens")].replace(",", "")
            # Don't multiply straight for 10**18 to avoid float precision issues. Supporting 3 decimals.
            amount_E18 = int(float(amount) * 10**3) * 10**15

            if beneficiary in recipient_to_amount_E18:
                recipient_to_amount_E18[beneficiary] += amount_E18
            else:
                recipient_to_amount_E18[beneficiary] = amount_E18

            flip_total_E18 += amount_E18
            total_rows += 1

    assert (
        sum(recipient_to_amount_E18.values()) == flip_total_E18
    ), "Total amount doesn't match"

    print("Deployer balance: ", flip.balanceOf(DEPLOYER) / E_18)
    print(f"Amount of FLIP required    = {flip_total_E18/E_18:,}")
    assert flip_total_E18 <= flip.balanceOf(
        DEPLOYER
    ), "Not enough FLIP tokens to fund the vestings"
    expected_final_balance = flip.balanceOf(DEPLOYER) - flip_total_E18

    # For live deployment, add a confirmation step to allow the user to verify the row.
    print(f"DEPLOYER = {DEPLOYER}")
    print(f"FLIP = {flip_address}")

    print(f"Total amount of FLIP to airdrop    = {flip_total_E18/E_18:,}")
    print(f"Number of rows = {total_rows}")
    print(f"Number of unique receivers = {len(recipient_to_amount_E18)}")
    print(f"Initial deployer's FLIP balance = {flip.balanceOf(DEPLOYER):,}")
    print(f"Initial deployer's FLIP balance / E_18 = {flip.balanceOf(DEPLOYER)/E_18:,}")
    print(f"Final deployer's FLIP balance   = {expected_final_balance:,}")
    print(f"Final deployer's FLIP balance / E_18   = {expected_final_balance / E_18:,}")

    transfer_batch_size = 100
    batches = []

    # Iterate over batches of 100 lists
    for i in range(0, len(recipient_to_amount_E18), transfer_batch_size):
        recipient_batch = list(recipient_to_amount_E18.keys())[
            i : i + transfer_batch_size
        ]
        amounts_E18_batch = list(recipient_to_amount_E18.values())[
            i : i + transfer_batch_size
        ]

        assert len(recipient_batch) == len(amounts_E18_batch), "Length doesn't match"
        assert len(recipient_batch) <= transfer_batch_size, "Length doesn't match"
        # Process the batch
        total_amount_batch = 0
        for amount in amounts_E18_batch:
            total_amount_batch += amount
        batches.append([recipient_batch, amounts_E18_batch, total_amount_batch])

    total_amount_batches = 0
    total_number_recipients = 0
    print(f"\nNumber of batches = {len(batches)}")
    for i, batch in enumerate(batches):
        print(
            f"   Batch {i} has {len(batch[0]):>3} recipients and a total of {batch[2]/E_18} FLIP"
        )
        total_amount_batches += batch[2]
        total_number_recipients += len(batch[0])
    assert total_amount_batches == flip_total_E18, "Total amount doesn't match"
    assert total_number_recipients == len(
        recipient_to_amount_E18
    ), "Total number of recipients doesn't match"

    print(f"Total unique recipients = {total_number_recipients}")
    print(f"Total amount to airdrop = {total_amount_batches/E_18}")
    prompt_user_continue_or_break(
        "Airdrop with the parameter above. Approving Token", True
    )

    # Multisend using wenTokens optimized airdrop tool
    # Same address in mainnet and test networks
    airdrop_contract = IAirdropContract(address_wenTokens)

    flip.approve(
        address_wenTokens,
        flip_total_E18,
        {"from": DEPLOYER, "required_confs": 1},
    )

    prompt_user_continue_or_break("Token approved. Proceedding with the transfer", True)

    for batch in batches:
        print("Airdropping batch with total amount of ", batch[2] / E_18, " FLIP")
        airdrop_contract.airdropERC20(
            flip,
            batch[0],
            batch[1],
            batch[2],
            {"from": DEPLOYER, "required_confs": 1},
        )

    print("Airdrop done!")

    # Wait to make sure all contracts are deployed and we don't get a failure when doing checks
    if chain.id not in [eth_localnet, arb_localnet, hardhat]:
        print("Waiting for a short time for safety...")
        time.sleep(12)

    print("Verifying airdop...")
    assert flip.allowance(DEPLOYER, address_wenTokens) == 0, "Allowance not correct"

    for i, (recipient, amount_E18) in enumerate(recipient_to_amount_E18.items()):
        balance = flip.balanceOf(recipient)
        assert (
            flip.balanceOf(recipient) == amount_E18
        ), f"Tokens not transferred correctly, expecting {amount_E18} but got {balance} for recipient {recipient}"
        print(
            f"- {str(i):>3}: Recipient {recipient} has been airdropped {str(amount_E18/E_18):>8} FLIP"
        )

    assert expected_final_balance == flip.balanceOf(DEPLOYER), "Incorrect final balance"

    print(f"Final deployer's FLIP balance   = {expected_final_balance}")
    print(f"Final deployer's FLIP balance / E_18  = {expected_final_balance / E_18}")

    print("\n😎😎 Airdrop completed and verified! 😎😎\n")
