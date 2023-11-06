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
from datetime import datetime

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

AUTONOMY_SEED = os.environ["SEED"]
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]

print(f"DEPLOYER = {DEPLOYER}")
network.priority_fee("1 gwei")


def main():

    # TODO: Ensure vesting schedule is correct. Leaving cliff to 1 day for safety. Enter env variables?
    # TODO: If we want noStaking_cliff to be a precise timestamp, remove the the chain.time() addition
    # Vesting schedule
    noStaking_cliff = DAY
    noStaking_end = noStaking_cliff + YEAR
    staking_start = YEAR
    staking_end = staking_start + YEAR

    governor = os.environ["GOV_KEY"]
    revoker_address = os.environ["REVOKER_ADDRESS"]
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
                revoker = revoker_address
            elif revokable == "Disabled":
                revoker = ZERO_ADDR
            else:
                raise Exception(f"Incorrect revokability parameter {revokable}")

            amount_E18 = amount * E_18

            vesting_list.append(
                [beneficiary, amount_E18, lockup_type, transferable, revoker]
            )

            flip_total_E18 += amount_E18

    print("Deployer balance: ", flip.balanceOf(DEPLOYER) // E_18)
    assert flip_total_E18 <= flip.balanceOf(
        DEPLOYER
    ), "Not enough FLIP tokens to fund the vestings"
    final_balance = (flip.balanceOf(DEPLOYER) - flip_total_E18) // E_18

    # For live deployment, add a confirmation step to allow the user to verify the row.
    print(f"DEPLOYER = {DEPLOYER}")
    print(f"FLIP = {flip_address}")
    print(f"GOVERNOR & REVOKER = {governor}")
    print(f"REVOKER = {revoker_address}")

    print(f"SC_GATEWAY_ADDRESS = {sc_gateway_address}")
    print(f"ST_MINTER_ADDRESS  =  {stMinter_address}")
    print(f"ST_BURNER_ADDRESS  =  {stBurner_address}")
    print(f"ST_FLIP_ADDRESS    =  {stFlip_address}")

    print(f"Number of staking vesting contracts = {number_staking}")
    print(f"Number of non-staking vesting contracts = {number_noStaking}")
    print(f"Total number of contracts = {number_staking+number_noStaking}")
    print(f"Total amount of FLIP to vest    = {flip_total_E18//E_18:,}")
    print(f"Initial deployer's FLIP balance = {flip.balanceOf(DEPLOYER)//E_18:,}")
    print(f"Final deployer's FLIP balance   = {final_balance:,}")

    # Calculate final vesting times
    current_time = chain.time()
    deploy_staking_start = staking_start + current_time
    deploy_staking_end = staking_end + current_time
    deploy_noStaking_cliff = noStaking_cliff + current_time
    deploy_noStaking_end = noStaking_end + current_time

    print(f"Current date = {datetime.fromtimestamp(current_time)} ({current_time})")

    print("Staking vesting parameters")
    print(
        f"   - Linear start = {staking_start//YEAR} year(s), {(staking_start % YEAR)//MONTH} month(s) and {((staking_start % YEAR)%MONTH)//DAY} day(s)"
    )
    print(
        f"   - Linear start date = {datetime.fromtimestamp(deploy_staking_start)} ({deploy_staking_start})"
    )

    print(
        f"   - Linear end = {staking_end//YEAR} year(s), {(staking_end % YEAR)//MONTH} month(s) and {((staking_end % YEAR)%MONTH)//DAY} day(s)"
    )
    print(
        f"   - Linear end date = {datetime.fromtimestamp(deploy_staking_end)} ({deploy_staking_end})"
    )

    print("Non-Staking vesting parameters")
    print(
        f"   - Cliff = {noStaking_cliff//YEAR} year(s), {(noStaking_cliff % YEAR)//MONTH} month(s) and {((noStaking_cliff % YEAR)%MONTH)//DAY} day(s)"
    )
    print(
        f"   - Cliff date = {datetime.fromtimestamp(deploy_noStaking_cliff)} ({deploy_noStaking_cliff})"
    )

    print(
        f"   - End = {noStaking_end//YEAR} year(s), {(noStaking_end % YEAR)//MONTH} month(s) and {((noStaking_end % YEAR)%MONTH)//DAY} day(s)"
    )
    print(
        f"   - End date = {datetime.fromtimestamp(deploy_noStaking_end)} ({deploy_noStaking_end})"
    )

    prompt_user_continue_or_break("Deployment with the parameter above", True)

    if chain.id == eth_mainnet or chain.id == arb_mainnet:
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
                deploy_staking_start,
                deploy_staking_end,
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
                deploy_noStaking_cliff,
                deploy_noStaking_end,
                transferable_beneficiary,
            )
        else:
            raise Exception(
                f"Incorrect lockup type parameter {lockup_type}. Should have been dropped earlier"
            )
        vesting.append(tv)

    print("Checking all the transaction receipts...")
    for vesting in vesting_list:
        web3.eth.wait_for_transaction_receipt(vesting[-1].tx.txid)

    # Wait to make sure all contracts are deployed and we don't get a failure when doing checks
    if chain.id in [eth_localnet, arb_localnet, hardhat]:
        print("Waiting for some blocks for safety")
        chain.sleep(24)

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
            assert tv.start() == deploy_staking_start, "Staking end not set correctly"
            assert tv.end() == deploy_staking_end, "NoStaking end not set correctly"

        else:
            assert (
                tv.cliff() == deploy_noStaking_cliff
            ), "NoStaking Cliff not set correctly"
            assert tv.end() == deploy_noStaking_end, "NoStaking end not set correctly"

        assert tv.getBeneficiary() == beneficiary, "Beneficiary not set correctly"
        assert tv.getRevoker() == revoker, "Revoker not set correctly"

        assert (
            tv.transferableBeneficiary() == transferable_beneficiary
        ), "Transferability not set correctly"

    prompt_user_continue_or_break(
        "Deployment of contracts finalized. Proceeding with token airdrop", True
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

    print("Address holder deployed at: ", addressHolder.address)

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
    addressHolder_address = os.environ["ADDERSS_HOLDER_ADDRESS"]
    stMinter_address = os.environ["ST_MINTER_ADDRESS"]
    stBurner_address = os.environ["ST_BURNER_ADDRESS"]
    stFlip_address = os.environ["ST_FLIP_ADDRESS"]
    address_holder = AddressHolder.at(f"0x{cleanHexStr(addressHolder_address)}")

    tx = address_holder.updateStakingAddresses(
        stMinter_address, stBurner_address, stFlip_address, {"from": DEPLOYER}
    )
    tx.info()


def updateStateChainGateway():
    addressHolder_address = os.environ["ADDERSS_HOLDER_ADDRESS"]
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
