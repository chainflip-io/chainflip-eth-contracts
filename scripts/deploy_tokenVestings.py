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
from utils import prompt_user_continue_or_break
from brownie import (
    chain,
    accounts,
    FLIP,
    AddressHolder,
    TokenVestingStaking,
    TokenVestingNoStaking,
    network,
)

# File should be formatted as a list of parameters. First line should be the headers with names of the
# parameters. The rest of the lines should be the values for each parameter. It should contain the
# parameters described in the order dictionary below but it can have others, which will be ignored.
VESTING_INFO_FILE = os.environ["VESTING_INFO_FILE"]
order = {"eth_address": 0, "amount": 1, "lockup_type": 2, "transferable_beneficiary": 3}
options_lockup_type = ["A", "B"]
options_transferable_beneficiary = ["Y", "N"]

# NOTE: Ensure vesting schedule is correct
vesting_time_cliff = QUARTER_YEAR
vesting_time_end = vesting_time_cliff + YEAR


AUTONOMY_SEED = os.environ["SEED"]
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]

print(f"DEPLOYER = {DEPLOYER}")
network.priority_fee("1 gwei")


def main():
    governor = os.environ["GOV_KEY"]
    sc_gateway_address = os.environ["SC_GATEWAY_ADDRESS"]
    flip_address = os.environ["FLIP_ADDRESS"]
    stMinter_address = os.environ.get("ST_MINTER_ADDRESS")
    stBurner_address = os.environ.get("ST_BURNER_ADDRESS")
    stFlip_address = os.environ.get("ST_FLIP_ADDRESS")

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

            vesting_list.append([beneficiary, amount, lockup_type, transferable])

            if lockup_type == "A":
                number_staking += 1
            else:
                number_noStaking += 1

            flip_total += amount

    # Vesting schedule
    current_time = chain.time()
    cliff = current_time + vesting_time_cliff
    end = current_time + vesting_time_end

    assert flip_total * E_18 <= flip.balanceOf(
        DEPLOYER
    ), "Not enough FLIP tokens to fund the vestings"
    final_balance = (flip.balanceOf(DEPLOYER) - flip_total * E_18) // E_18

    # For live deployment, add a confirmation step to allow the user to verify the row.
    print(f"DEPLOYER = {DEPLOYER}")
    print(f"FLIP = {flip_address}")
    print(f"GOVERNOR & REVOKER = {governor}")

    print(f"SC_GATEWAY_ADDRESS = {sc_gateway_address}")
    print(f"ST_MINTER_ADDRESS  =  {stMinter_address}")
    print(f"ST_BURNER_ADDRESS  =  {stBurner_address}")
    print(f"ST_FLIP_ADDRESS    =  {stFlip_address}")

    print(f"Number of staking vesting contracts = {number_staking}")
    print(f"Number of non-staking vesting contracts = {number_noStaking}")
    print(f"Total number of contracts = {number_staking+number_noStaking}")
    print(f"Vesting cliff (only for non-staking) = {vesting_time_cliff//MONTH} months")
    print(
        f"Vesting end (staking & non-staking)  = {vesting_time_end//YEAR} years and {(vesting_time_end % YEAR)//MONTH} months"
    )
    print(f"Total amount of FLIP to vest    = {flip_total:,}")
    print(f"Initial deployer's FLIP balance = {flip.balanceOf(DEPLOYER)//E_18:,}")
    print(f"Final deployer's FLIP balance   = {final_balance:,}")

    prompt_user_continue_or_break("Deployment with the parameter above", True)

    if chain.id == 1:
        prompt_user_continue_or_break(
            "\n[WARNING] You are about to deploy to the mainnet with the row above",
            False,
        )

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

    # Deploy the staking contracts
    for vesting in vesting_list:
        beneficiary, amount, lockup_type, transferable_beneficiary = vesting
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

    for i, vesting in enumerate(vesting_list):
        print(
            f"- {str(i):>2} Lockup type {vesting[2]}, contract with beneficiary {vesting[0]}, amount {str(vesting[1]):>8} FLIP and transferability {str(vesting[3]):<5} deployed at {vesting[4]}"
        )
    print("\n😎😎 Vesting contracts deployed successfully! 😎😎\n")

    assert final_balance == flip.balanceOf(DEPLOYER) // E_18, "Incorrect final balance"

    print(f"Final deployer's FLIP balance   = {final_balance:,}")


def stake_via_stProvider():
    token_vesting_address = os.environ["TOKEN_VESTING_ADDRESS"]
    token_vesting = TokenVestingStaking.at(f"0x{cleanHexStr(token_vesting_address)}")

    token_vesting.stakeToStProvider(1 * 10**18, {"from": DEPLOYER})


def unstake_from_stProvider():
    token_vesting_address = os.environ["TOKEN_VESTING_ADDRESS"]
    token_vesting = TokenVestingStaking.at(f"0x{cleanHexStr(token_vesting_address)}")

    token_vesting.unstakeFromStProvider(1 * 10**18, {"from": DEPLOYER})
