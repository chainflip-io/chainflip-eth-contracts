import sys
import os
import csv

sys.path.append(os.path.abspath("tests"))
from consts import *
from deploy import (
    deploy_addressHolder,
    deploy_tokenVestingStaking,
    deploy_tokenVestingNoStaking,
)
from brownie import (
    chain,
    accounts,
    FLIP,
    AddressHolder,
    TokenVestingStaking,
    TokenVestingNoStaking,
    network,
)

# File should be formatted as a list of beneficiary_addresses, the amount to vest separated by
# a space, followed by a true/false pool signaling if they canStake and then if the beneficiary
# can be transferred. Amount should be in Ether and will be converted to wei in this script.
VESTING_INFO_FILE = os.environ["VESTING_INFO_FILE"]

order = {"eth_address": 0, "amount": 1, "lockup_type": 2, "transferable_beneficiary": 3}
options_lockup_type = ["A", "B"]
options_transferable_beneficiary = ["Y", "N"]


def main():
    AUTONOMY_SEED = os.environ["SEED"]
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]

    governor = os.environ["GOV_KEY"]
    sc_gateway_address = os.environ["SC_GATEWAY_ADDRESS"]
    flip_address = os.environ["FLIP_ADDRESS"]
    stMinter_address = os.environ.get("ST_MINTER_ADDRESS") or ZERO_ADDR
    stBurner_address = os.environ.get("ST_BURNER_ADDRESS") or ZERO_ADDR
    stFlip_address = os.environ.get("ST_FLIP_ADDRESS") or ZERO_ADDR

    flip = FLIP.at(f"0x{cleanHexStr(flip_address)}")

    vesting_list = []
    number_staking = 0
    number_noStaking = 0
    flip_total = 0

    with open(VESTING_INFO_FILE, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')

        # Check the first row - parameter names
        first_row = next(reader)
        for parameter_name, position in order.items():
            assert first_row[position] == parameter_name, "Incorrect parameter name"

        # Read the rest of the rows
        for row in reader:
            print("row: ", row)
            assert len(row) == 4, "Incorrect number of parameters"

            beneficiary = row[order["eth_address"]]
            amount = int(row[order["amount"]])
            lockup_type = row[order["lockup_type"]]
            transferable = row[order["transferable_beneficiary"]]

            # Check that the row are valid
            assert (
                transferable in options_transferable_beneficiary
            ), "Incorrect transferability parameter"
            assert lockup_type in options_lockup_type, "Incorrect lockup type parameter"

            transferable = (
                True if row[order["transferable_beneficiary"]] == "Y" else False
            )

            vesting_list.append([beneficiary, amount, transferable, lockup_type])

            if lockup_type == "A":
                number_staking += 1
            else:
                number_noStaking += 1

            flip_total += amount

    # For live deployment, add a confirmation step to allow the user to verify the row.
    print(f"DEPLOYER = {DEPLOYER}")
    print(f"FLIP = {flip_address}")
    print(f"GOVERNOR & REVOKER = {governor}")

    print(f"SC_GATEWAY_ADDRESS = {sc_gateway_address}")
    print(f"ST_MINTER_ADDRESS = {stMinter_address}")
    print(f"ST_BURNER_ADDRESS = {stBurner_address}")
    print(f"ST_FLIP_ADDRESS = {stFlip_address}")

    print(f"Number of staking vesting contracts = {number_staking}")
    print(f"Number of non-staking vesting contracts = {number_noStaking}")
    print(f"Total amount of FLIP to vest = {flip_total}")

    # TODO: Should amounts be done in E_18?
    assert flip_total * E_18 <= flip.balanceOf(
        DEPLOYER
    ), "Not enough FLIP tokens to fund the vestings"

    if chain.id == 1:
        user_input = input(
            "\n[WARNING] You are about to deploy to the mainnet with the row above. Continue? [y/N] "
        )
        if user_input != "y":
            ## Gracefully exit the script with a message.
            sys.exit("Deployment cancelled by user")

    # Vesting schedule
    # TODO: Check that this vesting schedule is correct
    current_time = chain.time()
    cliff = current_time + QUARTER_YEAR
    end = cliff + YEAR

    # Deploying the address Holder
    addressHolder = deploy_addressHolder(
        DEPLOYER,
        AddressHolder,
        governor,
        sc_gateway_address,
        stMinter_address,
        stBurner_address,
        stFlip_address,
    )

    print("vesting_list: ", vesting_list)
    # Deploy the staking contracts
    for vesting in vesting_list:
        beneficiary, amount, transferable_beneficiary, lockup_type = vesting
        amount_E18 = amount * E_18

        if lockup_type == "A":

            tv = deploy_tokenVestingStaking(
                DEPLOYER,
                TokenVestingStaking,
                beneficiary,
                governor,
                end,
                transferable_beneficiary,
                addressHolder.address,
                flip,
                amount_E18,
            )
            assert (
                tv.addressHolder() == addressHolder.address
            ), "Address holder not set correctly"
            assert tv.FLIP() == flip.address, "FLIP not set correctly"

        else:
            tv = deploy_tokenVestingNoStaking(
                DEPLOYER,
                TokenVestingNoStaking,
                beneficiary,
                governor,
                cliff,
                end,
                transferable_beneficiary,
                flip,
                amount_E18,
            )
            assert tv.cliff() == cliff, "Cliff not set correctly"

        assert tv.getBeneficiary() == beneficiary, "Beneficiary not set correctly"
        assert tv.getRevoker() == governor, "Revoker not set correctly"

        assert (
            tv.transferableBeneficiary() == transferable_beneficiary
        ), "Transferability not set correctly"
        assert tv.end() == end, "End not set correctly"

        assert (
            flip.balanceOf(tv.address) == amount_E18
        ), "Tokens not transferred correctly"
        vesting.append(tv.address)

    print("\n😎😎 Staking vesting contracts deployed successfully! 😎😎\n")

    print("vesting_list: ", vesting_list)

    for i, vesting in enumerate(vesting_list):
        print(
            f"- {i}: Lockup type {vesting[3]}, contract with beneficiary {vesting[0]}, amount {vesting[1]} FLIP and transferability {str(vesting[2]):<5} deployed at {vesting[4]}"
        )
