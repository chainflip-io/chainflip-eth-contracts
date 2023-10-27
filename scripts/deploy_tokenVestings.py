import sys
import os
import csv

sys.path.append(os.path.abspath("tests"))
from consts import *
from deploy import (
    deploy_addressHolder,
    deploy_tokenVestingStaking,
    deploy_tokenVestingNoStaking,
    transaction_params,
)
from utils import prompt_user_continue_or_break
from brownie import (
    project,
    chain,
    accounts,
    FLIP,
    AddressHolder,
    TokenVestingStaking,
    TokenVestingNoStaking,
    network,
    web3,
)

_project = project.get_loaded_projects()[0]
IAirdropContract = _project.interface.IAirdrop
address_wenTokens = "0x2c952eE289BbDB3aEbA329a4c41AE4C836bcc231"

# File should be formatted as a list of parameters. First line should be the headers with names of the
# parameters. The rest of the lines should be the values for each parameter. It should contain the
# parameters described in the order dictionary below but it can have others, which will be ignored.
VESTING_INFO_FILE = os.environ["VESTING_INFO_FILE"]
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
options_lockup_type = ["Option A", "Option B", "Airdrop"]

# TODO: Ensure vesting schedule is correct. Leaving cliff to 1 day for safety
vesting_time_cliff = DAY
vesting_time_end = vesting_time_cliff + YEAR


AUTONOMY_SEED = os.environ["SEED"]
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]

print(f"DEPLOYER = {DEPLOYER}")
network.priority_fee("1 gwei")


def main():
    # TODO: Assumption that revoker and Address Holder's governor are the same
    governor = os.environ["GOV_KEY"]
    sc_gateway_address = os.environ["SC_GATEWAY_ADDRESS"]
    flip_address = os.environ["FLIP_ADDRESS"]
    stMinter_address = os.environ["ST_MINTER_ADDRESS"]
    stBurner_address = os.environ["ST_BURNER_ADDRESS"]
    stFlip_address = os.environ["ST_FLIP_ADDRESS"]

    flip = FLIP.at(f"0x{cleanHexStr(flip_address)}")

    vesting_list = []
    number_staking = 0
    number_noStaking = 0
    flip_total_E18 = 0

    with open(VESTING_INFO_FILE, newline="") as csvfile:
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

            # Check that all rows are valid
            lockup_type = row[columns.index("Final Choice Lock up Schedule")]

            if lockup_type == options_lockup_type[0]:
                number_staking += 1
            elif lockup_type == options_lockup_type[1]:
                number_noStaking += 1
            elif lockup_type == options_lockup_type[2]:
                # Skip the ones marked as Airdrop
                continue
            else:
                raise Exception(f"Incorrect lockup type parameter {lockup_type}")

            beneficiary = row[columns.index("Beneficiary Wallet Address")]
            amount = int(row[columns.index("# tokens")].replace(",", ""))
            transferable = row[
                columns.index("Address transfer enabled in smart contract?")
            ]
            revokable = row[columns.index("Yeet Function?")]

            assert web3.isAddress(
                beneficiary
            ), f"Incorrect beneficiary address {beneficiary}"

            if transferable in ["yes", "Yes"]:
                transferable = True
            elif transferable in ["no", "No"]:
                transferable = False
            else:
                raise Exception(f"Incorrect transferability parameter {transferable}")

            if revokable == "Enabled":
                revoker = governor
            elif revokable == "Disabled":
                revoker = ZERO_ADDR
            else:
                raise Exception(f"Incorrect revokability parameter {revokable}")

            amount_E18 = amount * E_18

            vesting_list.append(
                [beneficiary, amount_E18, lockup_type, transferable, revoker]
            )

            flip_total_E18 += amount_E18

    # Vesting schedule
    current_time = chain.time()
    cliff = current_time + vesting_time_cliff
    end = current_time + vesting_time_end

    assert flip_total_E18 <= flip.balanceOf(
        DEPLOYER
    ), "Not enough FLIP tokens to fund the vestings"
    final_balance = (flip.balanceOf(DEPLOYER) - flip_total_E18) // E_18

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
    print(
        f"Vesting cliff (only for non-staking) = {vesting_time_cliff//YEAR} years, {(vesting_time_cliff % YEAR)//MONTH} months and {((vesting_time_cliff % YEAR)%MONTH)//DAY} days"
    )
    print(
        f"Vesting end (staking & non-staking)  = {vesting_time_end//YEAR} years, {(vesting_time_end % YEAR)//MONTH} months and {((vesting_time_end % YEAR)%MONTH)//DAY} days"
    )
    print(f"Total amount of FLIP to vest    = {flip_total_E18//E_18:,}")
    print(f"Initial deployer's FLIP balance = {flip.balanceOf(DEPLOYER)//E_18:,}")
    print(f"Final deployer's FLIP balance   = {final_balance:,}")

    prompt_user_continue_or_break("Deployment with the parameter above", True)

    if chain.id == 1:
        prompt_user_continue_or_break(
            "\n[WARNING] You are about to deploy to the mainnet",
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

    # Deploy all the vesting contracts
    for vesting in vesting_list:
        (
            beneficiary,
            amount_E18,
            lockup_type,
            transferable_beneficiary,
            revoker,
        ) = vesting

        if lockup_type == options_lockup_type[0]:

            tv = deploy_tokenVestingStaking(
                DEPLOYER,
                TokenVestingStaking,
                beneficiary,
                revoker,
                end,
                transferable_beneficiary,
                addressHolder.address,
                flip,
            )

        elif lockup_type == options_lockup_type[1]:
            tv = deploy_tokenVestingNoStaking(
                DEPLOYER,
                TokenVestingNoStaking,
                beneficiary,
                revoker,
                cliff,
                end,
                transferable_beneficiary,
            )
        else:
            raise Exception(
                f"Incorrect lockup type parameter {lockup_type}. Should have been dropped earlier"
            )
        vesting.append(tv)

    # Wait to make sure all contracts are deployed and we don't get a failure when doing checks
    print("Waiting for all the transaction receipts...")
    for vesting in vesting_list:
        web3.eth.wait_for_transaction_receipt(vesting[-1].tx.txid)

    print("Verifying correct deployment of vesting contracts...")
    for vesting in vesting_list:
        (
            beneficiary,
            amount_E18,
            lockup_type,
            transferable_beneficiary,
            revoker,
            tv,
        ) = vesting

        if lockup_type == options_lockup_type[0]:
            assert (
                tv.addressHolder() == addressHolder.address
            ), "Address holder not set correctly"
            assert tv.FLIP() == flip.address, "FLIP not set correctly"
        else:
            assert tv.cliff() == cliff, "Cliff not set correctly"

        assert tv.getBeneficiary() == beneficiary, "Beneficiary not set correctly"
        assert tv.getRevoker() == revoker, "Revoker not set correctly"

        assert (
            tv.transferableBeneficiary() == transferable_beneficiary
        ), "Transferability not set correctly"
        assert tv.end() == end, "End not set correctly"

    prompt_user_continue_or_break(
        "Deployment of contracts finalized. Proceed with token airdrop?", True
    )

    # Multisend using wenTokens optimized airdrop tool
    vesting_addresses = [vesting[-1].address for vesting in vesting_list]
    vesting_amounts_E18 = [vesting[1] for vesting in vesting_list]
    assert len(vesting_addresses) == len(vesting_amounts_E18)

    total_amount_E18 = sum(vesting_amounts_E18)
    assert total_amount_E18 == flip_total_E18

    # Same address in mainnet and test networks
    airdrop_contract = IAirdropContract(address_wenTokens)

    required_confs = transaction_params()
    flip.approve(
        address_wenTokens,
        total_amount_E18,
        {"from": DEPLOYER, "required_confs": required_confs},
    )
    airdrop_contract.airdropERC20(
        flip,
        vesting_addresses,
        vesting_amounts_E18,
        total_amount_E18,
        {"from": DEPLOYER, "required_confs": required_confs},
    )
    assert flip.allowance(DEPLOYER, address_wenTokens) == 0, "Allowance not correct"

    for i, vesting in enumerate(vesting_list):
        (
            beneficiary,
            amount_E18,
            lockup_type,
            transferable_beneficiary,
            revoker,
            tv,
        ) = vesting
        assert (
            flip.balanceOf(tv.address) == amount_E18
        ), "Tokens not transferred correctly"
        print(
            f"- {str(i):>3}: Lockup type {lockup_type}, contract with beneficiary {beneficiary}, amount {str(amount_E18//E_18):>8} FLIP, transferability {str(transferable_beneficiary):<5}, revoker {str(revoker):<5}, deployed at {tv.address}"
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
