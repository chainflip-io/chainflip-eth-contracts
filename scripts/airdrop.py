import sys
import os
import os.path
import json
import csv

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import (
    chain,
    accounts,
    KeyManager,
    Vault,
    StakeManager,
    FLIP,
    Token,
    history,
    web3,
)
from deploy import deploy_set_Chainflip_contracts
from web3._utils.abi import get_constructor_abi, merge_args_and_kwargs
from web3._utils.events import get_event_data
from web3._utils.filters import construct_event_filter_params
from web3._utils.contracts import encode_abi
from .snapshot import snapshot


def main():
    rinkeby_flip_deployed = "0xbFf4044285738049949512Bd46B42056Ce5dD59b"
    # Use snapshot csv if it exists. Otherwise do a snapshot and airdrop
    if os.path.exists("snapshot.csv"):
        # To run in local hardhat node - this shall be removed when we do airdrop
        assert chain.id > 10
        if os.path.exists("snapshot_newFLIP.csv"):
            verifyAirdrop("snapshot.csv", "snapshot_newFLIP.csv")
        else:
            newFlipAddress, newStakeManager = airdrop("snapshot.csv")
            snapshot(web3.eth.block_number, newFlipAddress, "snapshot_newFLIP.csv")

    else:
        # To run in Rinkeby
        assert chain.id == 4
        # Using latest block for now as snapshot block
        snapshot(web3.eth.block_number, rinkeby_flip_deployed, "snapshot.csv")


def airdrop(snapshot_csv="snapshot.csv"):
    AUTONOMY_SEED = os.environ["SEED"]
    DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    print(f"DEPLOYER = {DEPLOYER}")

    (holderAccounts, holderBalances, totalBalance) = readCSVSnapshotChecksum(
        snapshot_csv
    )

    # Acccount running this script should have the balance required to do the airdrop

    # Problems:
    # - When deploying a new FLIP, the amount sent to airdropper is lower than what we need to airdrop -> Increase INIT supply?
    # - FLIP gives new flip to StakeManager and airdropper so airdropper will appear in the new snapshot -> Pass address of old StakeManager and give that balance to the new StakeManager
    airdropper = accounts[0]
    cf = deploy_set_Chainflip_contracts(
        airdropper, airdropper, KeyManager, Vault, StakeManager, FLIP, os.environ
    )

    assert cf.flip.balanceOf(airdropper) > totalBalance

    # Do Airdrop
    for i in range(len(holderAccounts)):
        cf.flip.transfer(holderAccounts[i], holderBalances[i], {"from": airdropper})

    return cf.flip.address, cf.stakeManager.address


def readCSVSnapshotChecksum(snapshot_csv):
    # Read csv file
    read_snapshot_csv = open(snapshot_csv, "r")
    holderAccounts = []
    holderBalances = []
    totalBalance = 0

    # Split columns while reading
    for a, b in csv.reader(read_snapshot_csv, delimiter=","):
        if "NumberHolders:" not in a:
            # Append each variable to a separate list
            holderAccounts.append(a)
            holderBalances.append(b)
            totalBalance += int(b)
        else:
            # Checksum in the last row
            print("Checksum verification")
            numberHolders = a.split(":")
            assert int(numberHolders[1]) == len(holderAccounts)
            assert totalBalance == int(b)

    # Printing for visibility purposes - amount has been checked
    print(snapshot_csv)
    print(totalBalance)
    print(len(holderAccounts))

    return (holderAccounts, holderBalances, totalBalance)


def verifyAirdrop(initalSnapshot, airdropSnapshot):
    (
        oldFlipHolderAccounts,
        oldFlipholderBalances,
        oldFliptotalBalance,
    ) = readCSVSnapshotChecksum(initalSnapshot)
    (
        newFLIPHolderAccounts,
        newFLIPholderBalances,
        newFLIPtotalBalance,
    ) = readCSVSnapshotChecksum(airdropSnapshot)

    # As mentioned before, newFLIPHolderAccounts will have two extra holders - newStakeManager and deployer which will be the first two lines

    # A pain to verify so commented for now
    # assert newFLIPHolderAccounts[0] == cf.flip.balanceOf(newStakeManager)
    assert newFLIPHolderAccounts[1] == accounts[0]

    # Delete both holders
    del newFLIPHolderAccounts[0:2]
    del newFLIPholderBalances[0:2]

    # We will be able to compare oldFliptotalBalance with newFLIPtotalBalance whenever we can set the INIT_SUPPLY when deploying FLIP
    assert len(oldFlipHolderAccounts) == len(newFLIPHolderAccounts)
    assert len(oldFlipholderBalances) == len(newFLIPholderBalances)

    for i in range(len(oldFlipHolderAccounts)):
        # Cannot compare pure balances here since oldHolders are in Rinkeby and new ones local
        assert oldFlipHolderAccounts[i] == newFLIPHolderAccounts[i]
        assert oldFlipholderBalances[i] == newFLIPholderBalances[i]
