import sys
import os
import json

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import chain, accounts, TokenVesting, FLIP, network

# File should be formatted as a list of beneficiary_addresses, the amount to vest separated by
# a space, followed by a true/false pool signaling if they canStake and then if the beneficiary
# can be transferred.
VESTING_INFO_FILE = os.environ["VESTING_INFO_FILE"]


def main():
    # Set the priority fee for all transactions
    network.priority_fee("1 gwei")

    AUTONOMY_SEED = os.environ["SEED"]
    DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    print(f"DEPLOYER = {DEPLOYER}")

    governor = os.environ["GOV_KEY"]
    # TODO: To potentially be updated with the SC_GATEWAY_REFERENCE_ADDRESS
    sc_gateway_address = os.environ["SC_GATEWAY_ADDRESS"]
    flip_address = os.environ["FLIP_ADDRESS"]

    vestings_list = []
    total_amount = 0

    required_confs = 1 if (chain.id == 31337) else 4

    # Obtain a list of lists with the parameters parsed and checked that they are valid
    with open(VESTING_INFO_FILE, "r") as f:
        for line in f:
            line = line.strip()  # Remove leading/trailing whitespaces and line breaks
            parameters = line.split()  # Split the line by whitespaces
            assert len(parameters) == 4, "Incorrect number of parameters"
            # Check that the parameters are valid
            if parameters[2] == "staking":
                staking = True
            elif parameters[2] == "notStaking":
                staking = False
            else:
                raise Exception("Panic! Unknown staking parameter")
            if parameters[3] == "true":
                transferable = True
            elif parameters[3] == "false":
                transferable = False
            else:
                raise Exception("Panic! Unknown transferability parameter")

            ## Continue parsing in some way
            vestings_list.append(
                [parameters[0], int(parameters[1]), staking, transferable]
            )
            total_amount += int(parameters[1])

    # For live deployment, add a confirmation step to allow the user to verify the parameters.
    if chain.id == 1:
        user_input = input(
            "\n[WARNING] You are about to deploy to the mainnet with the parameters above. Continue? [y/N] "
        )
        if user_input != "y":
            ## Gracefully exit the script with a message.
            sys.exit("Deployment cancelled by user")

    # TODO: Add some printing and confirmation of the deployment parameters
    flip = FLIP.at(f"0x{cleanHexStr(flip_address)}")
    assert total_amount <= flip.balanceOf(
        DEPLOYER
    ), "Not enough FLIP tokens to fund the vestings"

    # Deploy the contracts
    for vesting in vestings_list:
        beneficiary = vesting[0]
        amount = vesting[1]
        staking = vesting[2]
        transferable = vesting[3]

        current_time = chain.time()

        # Vesting schedule
        # TODO: Check that this vesting shcedule is correct
        if staking:
            cliff = end = current_time + YEAR
        else:
            cliff = current_time + QUARTER_YEAR
            end = cliff + YEAR

        tx = TokenVesting.deploy(
            beneficiary,
            governor,
            cliff,
            end,
            staking,
            transferable,
            sc_gateway_address,
            {"from": DEPLOYER, "required_confs": required_confs},
        )
        assert tx.getBeneficiary() == beneficiary, "Beneficiary not set correctly"
        assert tx.getRevoker() == governor, "Revoker not set correctly"
        assert tx.canStake() == staking, "Staking not set correctly"
        assert (
            tx.stateChainGateway() == sc_gateway_address
        ), "SC Gateway not set correctly"
        assert (
            tx.beneficiaryCanBeTransferred() == transferable
        ), "Transferability not set correctly"
        assert tx.cliff() == cliff, "Cliff not set correctly"
        assert tx.end() == end, "End not set correctly"

        # Mint the tokens to the vesting contract
        flip.transfer(tx.address, amount, {"from": DEPLOYER, "required_confs": 1})

        assert flip.balanceOf(tx.address) == amount, "Tokens not transferred correctly"
