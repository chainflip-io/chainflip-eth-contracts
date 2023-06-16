import sys
import os
import json

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import (
    chain,
    accounts,
    KeyManager,
    Vault,
    StateChainGateway,
    FLIP,
    MockUSDC,
    DeployerContract,
    CFReceiverMock,
    AddressChecker,
)
from deploy import deploy_Chainflip_contracts, deploy_usdc_contract


def main():
    AUTONOMY_SEED = os.environ["SEED"]
    DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    print(f"DEPLOYER = {DEPLOYER}")

    # Check that all environment variables are set when deploying to a live network.
    # SEED and the endpoint are checked automatically by Brownie.
    env_var_names = [
        "AGG_KEY",
        "GOV_KEY",
        "COMM_KEY",
        "GENESIS_STAKE",
        "NUM_GENESIS_VALIDATORS",
    ]
    for env_var_name in env_var_names:
        if env_var_name not in os.environ:
            raise Exception(f"Environment variable {env_var_name} is not set")

    # For live deployment, add a confirmation step to allow the user to verify the parameters.
    if chain.id == 1:
        # Print all the environment variables for mainnet deployment.
        print("\nTo be deployed with parameters\n----------------------------")
        print(f"  ChainID: {chain.id} - ETHEREUM MAINNET")
        print(f"  Deployer: {DEPLOYER}")
        print(f"  Safekeeper & GovKey: {os.environ['GOV_KEY']}")
        print(f"  Community Key: {os.environ['COMM_KEY']}")
        print(f"  Aggregate Key: {os.environ['AGG_KEY']}")
        print(f"  Genesis Stake: {os.environ['GENESIS_STAKE']}")
        print(f"  Genesis Stake / E_18: {int(os.environ['GENESIS_STAKE'])/E_18}")
        print(f"  Num Genesis Validators: {os.environ['NUM_GENESIS_VALIDATORS']}")
        print(
            f"\nFLIP tokens will be minted to the Safekeeper account {os.environ['GOV_KEY']}"
        )
        user_input = input(
            "\n[WARNING] You are about to deploy to the mainnet with the parameters above. Continue? [y/N] "
        )
        if user_input != "y":
            ## Gracefully exit the script with a message.
            sys.exit("Deployment cancelled by user")

    cf = deploy_Chainflip_contracts(
        DEPLOYER,
        KeyManager,
        Vault,
        StateChainGateway,
        FLIP,
        DeployerContract,
        AddressChecker,
        os.environ,
    )

    # Deploy extra contracts on local/devnets networks. Deploy USDC mock token to test
    # swaps and liquidity provision, CFReceiverMock to test cross-chain messaging.
    localnet_chainId = 10997
    if chain.id == localnet_chainId:
        cf.mockUSDC = deploy_usdc_contract(DEPLOYER, MockUSDC, cf_accs[0:10])
        cf.cfReceiverMock = DEPLOYER.deploy(CFReceiverMock, cf.vault)

    addressDump = {
        "KEY_MANAGER_ADDRESS": cf.keyManager.address,
        "SC_GATEWAY_ADDRESS": cf.stateChainGateway.address,
        "VAULT_ADDRESS": cf.vault.address,
        "FLIP_ADDRESS": cf.flip.address,
        "ADDRESS_CHECKER_ADDRESS": cf.addressChecker.address,
    }

    print("Deployed with parameters\n----------------------------")
    print(f"  ChainID: {chain.id}")
    print(f"  Deployer:   {cf.deployer}")
    print(f"  Safekeeper: {cf.safekeeper}")
    print(f"  GovKey:     {cf.gov}")
    print(f"  Community Key: {cf.communityKey}")
    print(f"  Aggregate Key: {cf.keyManager.getAggregateKey()}")
    print(f"  Genesis Stake: {cf.genesisStake}")
    print(f"  Genesis Stake / E_18: {cf.genesisStake/E_18}")
    print(f"  Num Genesis Validators: {cf.numGenesisValidators}" + "\n")

    print("Deployed contract addresses\n----------------------------")
    print(f"  DeployerContract: {cf.deployerContract.address}")
    print(f"  KeyManager: {cf.keyManager.address}")
    print(f"  StateChainGateway: {cf.stateChainGateway.address}")
    print(f"  FLIP: {cf.flip.address}")
    print(f"  Vault: {cf.vault.address}")
    print(f"  AddressChecker: {cf.addressChecker.address}")
    if chain.id == localnet_chainId:
        print(f"  USDC: {cf.mockUSDC.address}")
        addressDump["USDC_ADDRESS"] = cf.mockUSDC.address
        print(f"  CfReceiver Mock: {cf.mockUSDC.address}")
        addressDump["CF_RECEIVER_ADDRESS"] = cf.cfReceiverMock.address

    print("\n😎😎 Deployment success! 😎😎")

    if DEPLOY_ARTEFACT_ID:
        dir_path = os.path.dirname(os.path.abspath(__file__)) + "/.artefacts"

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        with open(f"{dir_path}/{DEPLOY_ARTEFACT_ID}.json", "w") as output_file:
            json.dump(addressDump, output_file, indent=2)
