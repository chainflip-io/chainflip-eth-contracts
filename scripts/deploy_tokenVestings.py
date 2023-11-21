import sys
import os
import csv
import time

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
from datetime import datetime

_project = project.get_loaded_projects()[0]
IAirdropContract = _project.interface.IAirdrop
address_wenTokens = "0x2c952eE289BbDB3aEbA329a4c41AE4C836bcc231"

# File should be formatted as a list of parameters. First line should be the headers with names of the
# parameters. The rest of the lines should be the values for each parameter. It should contain the
# parameters described in the order dictionary below but it can have others, which will be ignored.
VESTING_INFO_FILE = os.environ["VESTING_INFO_FILE"]
DEPLOYMENT_INFO_FILE = os.environ["DEPLOYMENT_INFO_FILE"]
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

# Vesting set to 1 year
vesting_period = YEAR
# Vesting schedule
noStaking_cliff = int(os.environ["STAKING_CLIFF_TIMESTAMP"])  # 1700740800 TGE
noStaking_end = noStaking_cliff + vesting_period
staking_start = int(os.environ["NO_STAKING_START_TIMESTAMP"])  # 1700740800 TGE
staking_end = staking_start + vesting_period


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

    revoker_address = os.environ[
        "REVOKER_ADDRESS"
    ]  # 0x38a4BCC04f5136e6408589A440F495D7AD0F34DB
    # AddressHolder governor
    governor = os.environ["GOV_KEY"]  # 0x38a4BCC04f5136e6408589A440F495D7AD0F34DB
    sc_gateway_address = os.environ[
        "SC_GATEWAY_ADDRESS"
    ]  # 0x6995Ab7c4D7F4B03f467Cf4c8E920427d9621DBd
    flip_address = os.environ[
        "FLIP_ADDRESS"
    ]  # 0x826180541412D574cf1336d22c0C0a287822678A
    stMinter_address = os.environ["ST_MINTER_ADDRESS"]
    stBurner_address = os.environ["ST_BURNER_ADDRESS"]
    stFlip_address = os.environ["ST_FLIP_ADDRESS"]

    flip = FLIP.at(f"0x{cleanHexStr(flip_address)}")

    vesting_list = []
    number_staking = 0
    number_noStaking = 0
    flip_total_E18 = 0

    if not os.path.isfile(DEPLOYMENT_INFO_FILE):
        prompt_user_continue_or_break("Starting deployment from scratch", True)

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

                if lockup_type == options_lockup_type[0]:
                    number_staking += 1
                elif lockup_type == options_lockup_type[1]:
                    number_noStaking += 1
                elif lockup_type == options_lockup_type[2]:
                    # Skip the ones marked as Airdrop
                    print(f"Skipping row marked as Airdrop {row}")
                    continue
                else:
                    raise Exception(f"Incorrect lockup type parameter {lockup_type}")

                # Check transferability
                transferable = row[
                    columns.index("Address transfer enabled in smart contract?")
                ]

                if transferable in ["yes", "Yes"]:
                    transferable = True
                elif transferable in ["no", "No"]:
                    transferable = False
                elif transferable in ["", "No answer", "No Answer", "no answer"]:
                    # For unknwons and undetermined, we default to False
                    transferable = False
                else:
                    raise Exception(
                        f"Incorrect transferability parameter {transferable}"
                    )

                # Check revokability
                revokable = row[columns.index("Yeet Function?")]

                if revokable == "Enabled":
                    revoker = revoker_address
                elif revokable == "Disabled":
                    revoker = ZERO_ADDR
                elif revokable == "":
                    # For undetermined default to disabled
                    revoker = ZERO_ADDR
                else:
                    raise Exception(f"Incorrect revokability parameter {revokable}")

                # Check amount
                amount = int(row[columns.index("# tokens")].replace(",", ""))
                amount_E18 = amount * E_18

                vesting_list.append(
                    [beneficiary, amount_E18, lockup_type, transferable, revoker]
                )

                flip_total_E18 += amount_E18

        print("Deployer balance: ", flip.balanceOf(DEPLOYER) // E_18)
        print(f"Amount of FLIP required    = {flip_total_E18//E_18:,}")

        assert flip_total_E18 <= flip.balanceOf(
            DEPLOYER
        ), "Not enough FLIP tokens to fund the vestings"
        expected_final_balance = flip.balanceOf(DEPLOYER) - flip_total_E18
        assert number_staking + number_noStaking == len(vesting_list)

        # For live deployment, add a confirmation step to allow the user to verify the row.
        print(f"DEPLOYER = {DEPLOYER}")
        print(f"FLIP = {flip_address}")
        print(f"REVOKER = {revoker_address}")
        print(f"AddressHolder GOVERNOR = {governor}")

        print(f"SC_GATEWAY_ADDRESS = {sc_gateway_address}")
        print(f"ST_MINTER_ADDRESS  =  {stMinter_address}")
        print(f"ST_BURNER_ADDRESS  =  {stBurner_address}")
        print(f"ST_FLIP_ADDRESS    =  {stFlip_address}")

        print(f"Number of staking vesting contracts = {number_staking}")
        print(f"Number of non-staking vesting contracts = {number_noStaking}")
        print(f"Total number of contracts = {number_staking+number_noStaking}")
        print(f"Total amount of FLIP to vest    = {flip_total_E18//E_18:,}")
        print(f"Initial deployer's FLIP balance = {flip.balanceOf(DEPLOYER):,}")
        print(
            f"Initial deployer's FLIP balance // E_18 = {flip.balanceOf(DEPLOYER)//E_18:,}"
        )
        print(f"Final deployer's FLIP balance   = {expected_final_balance:,}")
        print(
            f"Final deployer's FLIP balance // E_18   = {expected_final_balance // E_18:,}"
        )

        # Calculate final vesting times
        current_time = chain.time()
        assert staking_start > current_time
        assert staking_end > current_time
        assert noStaking_cliff > current_time
        assert noStaking_end > current_time
        relative_staking_start = staking_start - current_time
        relative_staking_end = staking_end - current_time
        relative_noStaking_cliff = noStaking_cliff - current_time
        relative_noStaking_end = noStaking_end - current_time

        print(f"Current date = {datetime.fromtimestamp(current_time)} ({current_time})")

        print("Staking vesting parameters")
        print(
            f"   - Staking starts in {relative_staking_start//YEAR} year(s), {(relative_staking_start % YEAR)//MONTH} month(s), {((relative_staking_start % YEAR)%MONTH)//DAY} day(s) and {(((relative_staking_start % YEAR)%MONTH)%DAY)//HOUR} hour(s)"
        )
        print(
            f"   - Staking start date = {datetime.fromtimestamp(staking_start)} ({staking_start})"
        )

        print(
            f"   - Staking ends in {relative_staking_end//YEAR} year(s), {(relative_staking_end % YEAR)//MONTH} month(s) and {((relative_staking_end % YEAR)%MONTH)//DAY} day(s)"
        )
        print(
            f"   - Staking end date = {datetime.fromtimestamp(staking_end)} ({staking_end})"
        )

        print("Non-Staking vesting parameters")
        print(
            f"   - Cliff in {relative_noStaking_cliff//YEAR} year(s), {(relative_noStaking_cliff % YEAR)//MONTH} month(s) and {((relative_noStaking_cliff % YEAR)%MONTH)//DAY} day(s) and {(((relative_noStaking_cliff % YEAR)%MONTH)%DAY)//HOUR} hour(s)"
        )
        print(
            f"   - Cliff date = {datetime.fromtimestamp(noStaking_cliff)} ({noStaking_cliff})"
        )

        print(
            f"   - End in {relative_noStaking_end//YEAR} year(s), {(relative_noStaking_end % YEAR)//MONTH} month(s) and {((relative_noStaking_end % YEAR)%MONTH)//DAY} day(s)"
        )
        print(
            f"   - End date = {datetime.fromtimestamp(noStaking_end)} ({noStaking_end})"
        )

        prompt_user_continue_or_break("Deployment with the parameter above", True)

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
                    staking_start,
                    staking_end,
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
                    noStaking_cliff,
                    noStaking_end,
                    transferable_beneficiary,
                )
            else:
                raise Exception(
                    f"Incorrect lockup type parameter {lockup_type}. Should have been dropped earlier"
                )
            vesting.append(tv)

        # Wait to make sure all contracts are deployed and we don't get a failure when doing checks
        if chain.id not in [eth_localnet, arb_localnet, hardhat]:
            print("Waiting for a short time for safety...")
            time.sleep(36)

        # Write the data to a CSV file
        print(f"Storing deployment info in {DEPLOYMENT_INFO_FILE}")
        with open(DEPLOYMENT_INFO_FILE, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(vesting_list)

        # AddressHolder deployment will already wait for several confirmations
        print("Address holder deployed at: ", addressHolder.address)

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
                assert tv.start() == staking_start, "Staking end not set correctly"
                assert tv.end() == staking_end, "NoStaking end not set correctly"

            else:
                assert (
                    tv.cliff() == noStaking_cliff
                ), "NoStaking Cliff not set correctly"
                assert tv.end() == noStaking_end, "NoStaking end not set correctly"

            assert tv.getBeneficiary() == beneficiary, "Beneficiary not set correctly"
            assert tv.getRevoker() == revoker, "Revoker not set correctly"

            assert (
                tv.transferableBeneficiary() == transferable_beneficiary
            ), "Transferability not set correctly"

    prompt_user_continue_or_break(
        "Deployment of contracts finalized. Proceeding with token airdrop", True
    )

    vesting_list = []
    with open(DEPLOYMENT_INFO_FILE, "r") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            # Format values appropriately
            row[1] = int(row[1])
            row[3] = True if row[3] == "True" else False
            vesting_list.append(row)

    # Multisend using wenTokens optimized airdrop tool
    vesting_addresses = [vesting[5] for vesting in vesting_list]
    vesting_amounts_E18 = [vesting[1] for vesting in vesting_list]
    assert len(vesting_addresses) == len(vesting_amounts_E18)

    if "expected_final_balance" not in locals():
        expected_final_balance = flip.balanceOf(DEPLOYER) - sum(vesting_amounts_E18)

    total_amount_E18 = sum(vesting_amounts_E18)

    # Same address in mainnet and test networks
    airdrop_contract = IAirdropContract(address_wenTokens)

    flip.approve(
        address_wenTokens,
        total_amount_E18,
        {"from": DEPLOYER, "required_confs": 1},
    )
    airdrop_contract.airdropERC20(
        flip,
        vesting_addresses,
        vesting_amounts_E18,
        total_amount_E18,
        {"from": DEPLOYER, "required_confs": 1},
    )
    # Wait to make sure all contracts are deployed and we don't get a failure when doing checks
    if chain.id not in [eth_localnet, arb_localnet, hardhat]:
        print("Waiting for a short time for safety...")
        time.sleep(12)

    assert flip.allowance(DEPLOYER, address_wenTokens) == 0, "Allowance not correct"

    for i, vesting in enumerate(vesting_list):
        (
            beneficiary,
            amount_E18,
            lockup_type,
            transferable_beneficiary,
            revoker,
            tv_address,
        ) = vesting
        assert (
            flip.balanceOf(tv_address) == amount_E18
        ), "Tokens not transferred correctly"
        print(
            f"- {str(i):>3}: Lockup type {lockup_type}, contract with beneficiary {beneficiary}, amount {str(amount_E18//E_18):>8} FLIP, transferability {str(transferable_beneficiary):<5}, revoker {str(revoker):<5}, deployed at {tv_address}"
        )

    print("\n😎😎 Vesting contracts deployed successfully! 😎😎\n")
    assert expected_final_balance == flip.balanceOf(DEPLOYER), "Incorrect final balance"

    print(f"Final deployer's FLIP balance   = {expected_final_balance}")
    print(f"Final deployer's FLIP balance // E_18  = {expected_final_balance // E_18}")


def release():
    token_vesting_address = os.environ["TOKEN_VESTING_ADDRESS"]
    token_vesting = TokenVestingStaking.at(f"0x{cleanHexStr(token_vesting_address)}")
    flip_address = os.environ["FLIP_ADDRESS"]
    tx = token_vesting.release(flip_address, {"from": DEPLOYER})
    tx.info()


def fund():
    token_vesting_address = os.environ["TOKEN_VESTING_ADDRESS"]
    token_vesting = TokenVestingStaking.at(f"0x{cleanHexStr(token_vesting_address)}")

    tx = token_vesting.fundStateChainAccount(JUNK_HEX, 1 * 10**18, {"from": DEPLOYER})
    tx.info()


def updateStakingAddresses():
    addressHolder_address = os.environ["ADDRESS_HOLDER_ADDRESS"]
    stMinter_address = os.environ["ST_MINTER_ADDRESS"]
    stBurner_address = os.environ["ST_BURNER_ADDRESS"]
    stFlip_address = os.environ["ST_FLIP_ADDRESS"]
    address_holder = AddressHolder.at(f"0x{cleanHexStr(addressHolder_address)}")

    tx = address_holder.updateStakingAddresses(
        stMinter_address, stBurner_address, stFlip_address, {"from": DEPLOYER}
    )
    tx.info()


def updateStateChainGateway():
    addressHolder_address = os.environ["ADDRESS_HOLDER_ADDRESS"]
    address_holder = AddressHolder.at(f"0x{cleanHexStr(addressHolder_address)}")
    sc_gateway_address = os.environ["SC_GATEWAY_ADDRESS"]

    tx = address_holder.updateStateChainGateway(sc_gateway_address, {"from": DEPLOYER})
    tx.info()


def stake_via_stProvider():
    token_vesting_address = os.environ["TOKEN_VESTING_ADDRESS"]
    token_vesting = TokenVestingStaking.at(f"0x{cleanHexStr(token_vesting_address)}")

    tx = token_vesting.stakeToStProvider(1 * 10**18, {"from": DEPLOYER})
    tx.info()


def unstake_from_stProvider():
    token_vesting_address = os.environ["TOKEN_VESTING_ADDRESS"]
    token_vesting = TokenVestingStaking.at(f"0x{cleanHexStr(token_vesting_address)}")

    tx = token_vesting.unstakeFromStProvider(1 * 10**18, {"from": DEPLOYER})
    tx.info()


def revoke():
    token_vesting_address = os.environ["TOKEN_VESTING_ADDRESS"]
    flip_address = os.environ["FLIP_ADDRESS"]

    token_vesting = TokenVestingStaking.at(f"0x{cleanHexStr(token_vesting_address)}")

    tx = token_vesting.revoke(flip_address, {"from": DEPLOYER})
    tx.info()
