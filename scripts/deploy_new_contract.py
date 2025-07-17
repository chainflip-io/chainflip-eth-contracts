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
    DeployerStateChainGateway,
    CFTester,
    Multicall,
    AddressChecker,
    ScUtils,
)
from deploy import (
    deploy_new_vault,
    deploy_new_stateChainGateway,
    deploy_new_keyManager,
    deploy_new_multicall,
    deploy_new_cfReceiver,
    deploy_address_checker,
    deploy_scUtils,
)


AUTONOMY_SEED = os.environ["SEED"]
DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {DEPLOYER}")


addressDump = {}

# This script is to deploy new contracts independently without redeploying all the Chainflip
# contract stack. This can be useful when deploying a new updated contract or to deploy
# a new contract from scratch. Run with:
# brownie run deploy_new_contract <function_name> --network <network_name>


def main():
    print()


def getKeyManager():
    # Get necessary environment variables and throw if they are not set
    KEY_MANAGER_ADDRESS = os.environ["KEY_MANAGER_ADDRESS"]
    keyManager = KeyManager.at(f"0x{cleanHexStr(KEY_MANAGER_ADDRESS)}")
    addressDump["KEY_MANAGER_ADDRESS"] = keyManager.address

    return keyManager


# This will deploy the new Vault. It requires a KeyManager to be deployed.
def deploy_vault():
    keyManager = getKeyManager()
    new_vault = deploy_new_vault(DEPLOYER, Vault, KeyManager, keyManager.address)
    addressDump["NEW_VAULT_ADDRESS"] = new_vault.address
    store_artifacts()


# This will deploy the new StateChainGateway.  It requires a KeyManager to be deployed.
def deploy_scGateway():
    keyManager = getKeyManager()
    FLIP_ADDRESS = os.environ["FLIP_ADDRESS"]
    redemption_delay = os.environ["REDEMPTION_DELAY"]
    flip_address = f"0x{cleanHexStr(FLIP_ADDRESS)}"

    (deployerStateChainGateway, new_stateChainGateway) = deploy_new_stateChainGateway(
        DEPLOYER,
        KeyManager,
        StateChainGateway,
        FLIP,
        DeployerStateChainGateway,
        keyManager.address,
        flip_address,
        MIN_FUNDING,
        redemption_delay,
    )
    addressDump["NEW_SC_GATEWAY_ADDRESS"] = new_stateChainGateway.address
    addressDump["DEPLOYER_SM"] = deployerStateChainGateway.address
    addressDump["FLIP_ADDRESS"] = flip_address

    store_artifacts()


# This will deploy the new KeyManager. For variables that are not passed
# we will use the values from the existing KeyManager.
def deploy_keyManager():
    keyManager = getKeyManager()

    aggKey = os.environ.get("AGG_KEY") or keyManager.getAggregateKey()
    govKey = os.environ.get("GOV_KEY") or keyManager.getGovernanceKey()
    communityKey = os.environ.get("COMM_KEY") or keyManager.getCommunityKey()

    new_keyManager = deploy_new_keyManager(
        DEPLOYER, KeyManager, aggKey, govKey, communityKey
    )
    addressDump["NEW_KEY_MANAGER_ADDRESS"] = new_keyManager.address

    store_artifacts()


def deploy_cfTester():
    VAULT_ADDRESS = os.environ["VAULT_ADDRESS"]
    vault = Vault.at(f"0x{cleanHexStr(VAULT_ADDRESS)}")
    addressDump["VAULT_ADDRESS"] = vault.address

    cfReceiver_mock = deploy_new_cfReceiver(DEPLOYER, CFTester, vault.address)
    addressDump["NEW_CF_RECEIVER"] = cfReceiver_mock.address
    store_artifacts()


# This will deploy the new Multicall. It requires the Vault address to be deployed.
def deploy_multicall():
    VAULT_ADDRESS = os.environ["VAULT_ADDRESS"]
    vault = Vault.at(f"0x{cleanHexStr(VAULT_ADDRESS)}")
    addressDump["VAULT_ADDRESS"] = vault.address

    new_multicall = deploy_new_multicall(DEPLOYER, Multicall, vault.address)
    addressDump["NEW_MULTICALL_ADDRESS"] = new_multicall.address
    store_artifacts()


def deploy_addr_checker():
    addressChecker = deploy_address_checker(DEPLOYER, AddressChecker)
    addressDump["ADDRESS_CHECKER"] = addressChecker.address
    store_artifacts()


def deploy_sc_utils():
    VAULT_ADDRESS = os.environ["VAULT_ADDRESS"]
    SC_GATEWAY_ADDRESS = os.environ["SC_GATEWAY_ADDRESS"]

    scUtilsAddress = deploy_scUtils(
        DEPLOYER, ScUtils, SC_GATEWAY_ADDRESS, VAULT_ADDRESS
    )
    addressDump["SC_UTILS"] = scUtilsAddress.address

    store_artifacts()


def store_artifacts():
    print("Deployed with parameters\n----------------------------")
    print(f"  ChainID: {chain.id}")
    print(f"  Deployer: {DEPLOYER}")

    print("\nLegacy contracts still in use\n----------------------------")
    if (
        "KEY_MANAGER_ADDRESS" in addressDump
        and not "NEW_KEY_MANAGER_ADDRESS" in addressDump
    ):
        print(f"  KeyManager: {addressDump['KEY_MANAGER_ADDRESS']}")
    if "FLIP_ADDRESS" in addressDump:
        print(f"  FLIP: {addressDump['FLIP_ADDRESS']}")
    if "VAULT_ADDRESS" in addressDump:
        print(f"  Vault: {addressDump['VAULT_ADDRESS']}")
    if "SC_GATEWAY_ADDRESS" in addressDump:
        print(f"  SC Gateway: {addressDump['SC_GATEWAY_ADDRESS']}")

    print("\nNew deployed contract addresses\n----------------------------")
    if "NEW_SC_GATEWAY_ADDRESS" in addressDump:
        print(f"  DeployerContract: {addressDump['DEPLOYER_SM']}")
        print(f"  StateChainGateway: {addressDump['NEW_SC_GATEWAY_ADDRESS']}")
    if "NEW_VAULT_ADDRESS" in addressDump:
        print(f"  Vault: {addressDump['NEW_VAULT_ADDRESS']}")
    if "NEW_KEY_MANAGER_ADDRESS" in addressDump:
        print(f"  KeyManager: {addressDump['NEW_KEY_MANAGER_ADDRESS']}")
    if "NEW_MULTICALL_ADDRESS" in addressDump:
        print(f"  Multicall: {addressDump['NEW_MULTICALL_ADDRESS']}")
    if "NEW_CF_RECEIVER" in addressDump:
        print(f"  Cf Receiver: {addressDump['NEW_CF_RECEIVER']}")
    if "ADDRESS_CHECKER" in addressDump:
        print(f"  AddressChecker: {addressDump['ADDRESS_CHECKER']}")
    if "SC_UTILS" in addressDump:
        print(f"  ScUtils: {addressDump['SC_UTILS']}")
    print("\n😎😎 Deployment success! 😎😎")

    if DEPLOY_ARTEFACT_ID:
        json_content = json.dumps(addressDump)

        dir_path = os.path.dirname(os.path.abspath(__file__)) + "/.artefacts/"

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        f = open(f"{dir_path}{DEPLOY_ARTEFACT_ID}.json", "w")
        f.write(json_content)
        f.close()
