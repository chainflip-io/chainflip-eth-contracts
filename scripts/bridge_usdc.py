import sys
import os
import json

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import (
    project,
    accounts,
    network,
    Token,
    KeyManager,
    Vault,
    StateChainGateway,
    FLIP,
    DeployerContract,
    AddressChecker,
)
from deploy import deploy_Chainflip_contracts
from brownie.convert import to_bytes
from shared_tests import *

import requests
import time

# Load the required interfaces
_project = project.get_loaded_projects()[0]
ITokenMessengerMock = _project.interface.ITokenMessengerMock
IMessageTransmitterMock = _project.interface.IMessageTransmitterMock
IAxelarGateway = _project.interface.IAxelarGateway


AUTONOMY_SEED = os.environ["SEED"]
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {DEPLOYER}")

# Set the priority fee for all transactions
network.priority_fee("1 gwei")

assert chain.id in [
    31337,
    43113,
    5,
], "This script is only for AVAX, Goerli and hardhat forks"

## Addresses in AVAX-Test (FUJI) and goerli
# FUJI
TOKENMESSENGER_CCTP_FUJI_ADDRESS = "0xeb08f243e5d3fcff26a9e38ae5520a669f4019d0"
USDC_FUJI_ADDRESS = "0x5425890298aed601595a70AB815c96711a31Bc65"
MESSAGE_TRANSMITTER_CCTP_FUJI = "0xa9fb1b3009dcb79e2fe346c16a604b8fa8ae0a79"
ETH_DESTINATION_DOMAIN = 0

aUSDC_FUJI_ADDRESS = "0x57F1c63497AEe0bE305B8852b354CEc793da43bB"
GATEWAY_FUJI_ADDRESS = "0xC249632c2D40b9001FE907806902f63038B737Ab"
# GAS_SERVICE_FUJI_ADDRESS = "0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6"

# Goerli
TOKENMESSENGER_CCTP_GOERLI_ADDRESS = "0xd0c3da58f55358142b8d3e06c1c30c5c6114efe8"
USDC_GOERLI_ADDRESS = "0x07865c6e87b9f70255377e024ace6630c1eaa37f"
MESSAGE_TRANSMITTER_CCTP_GOERLI = "0x26413e8157cd32011e726065a5462e97dd4d03d9"
FUJI_DESTINATION_DOMAIN = 1

GATEWAY_GOERLI_ADDRESS = "0xe432150cce91c13a887f7D836923d5597adD8E31"
aUSDC_GOERLI_ADDRESS = "0x254d06f33bDc5b8ee05b2ea472107E300226659A"

# Squid has the same address for all test networks
SQUID_MULTICALL_ADDRESS = "0x7a4F2BCdDf68C98202cbad13c4f3a04FF2405681"

# Bridging properties
tokens_to_transfer = 1 * 10**6

# NOTE: When forking a network (in another terminal) it spins a copy of the network
# with the default hardhat chain id 31337.

# To run on AVAX-Test fork (FUJI), spin AVAX-TEST fork on a separate terminal and run script:
#   npx hardhat node --fork https://api.avax-test.network/ext/bc/C/rpc
#   brownie run cctp avax-to-eth --network hardhat
# To run it on real avax-test:
#   brownie run cctp-avax-to-eth --network avax-test

# To run on Goerli fork, spin Goerli fork on a separate terminal and run script:
#   npx hardhat node --fork https://goerli.infura.io/v3/<INFURA_API>
#   brownie run cctp avax-to-eth --network hardhat
# Run it on real Goerli:
#   brownie run cctp-avax-to-eth --network goerli


def main():
    print("Starting cctp script")

    print(f"Chain ID: {chain.id}")

    action = input(
        "What do you want to do? [1] Bridge USDC/aUSDC [2] Get Attestation [3] Get & Submit attestation on egress chain: "
    )

    if action not in ["1", "2", "3"]:
        sys.exit("Wrong input")

    if action == "1" or action == "3":
        # Hardhat forking doesn't support having a particular chainID so we can't really identify
        # the chain. So we ask the user to specify it.
        fuji_to_goerli = input(
            "[1] FUJI (AVAX-TEST) to Goerli [2] Goerli to FUJI (AVAX-TEST): "
        )

        print("Choose the address that will be used to burn or mint USDC")
        depositor = input(
            "[1] Deploy new Vault [2] Use deployed Vault [3] Use SEED EOA : "
        )
        if depositor == "1":
            cf = deploy()
            depositor = cf.vault
        elif depositor == "2":
            ## Assumption that the AGG_KEY is the default one and we can sign with AGG_SIGNER_1
            depositor = input("Input the Vault address: in format '0x...' : ")
        elif depositor == "3":
            depositor = DEPLOYER
        else:
            sys.exit("Wrong input")

        mint_recipient_address = input(
            "Input the address that shall receive the minted USDC in format '0x...' : "
        )

        if action == "1":
            bridge_action = input(
                "[1] Bridge USDC via CCTP [2] Bridge aUSDC via Axelar : "
            )
            if bridge_action == "1":
                bridge_usdc(fuji_to_goerli, depositor, mint_recipient_address)
            elif bridge_action == "2":
                bridge_aUsdc(fuji_to_goerli, depositor, mint_recipient_address)
        elif action == "3":
            message = input(
                "We will get the attestation and submit it.\nInput the message emitted in the source chain in format '0x...' : "
            )
            get_and_submit_attestation(
                message, fuji_to_goerli, depositor, mint_recipient_address
            )

    elif action == "2":
        message = input(
            "Input the message emitted in the source chain in format '0x...' : "
        )
        attestation = get_attestation(message)
        print(f"attestation: {attestation}")


# Unclear if we want to deploy new contracts or if we want to point to already deployed ones
def deploy():
    return deploy_Chainflip_contracts(
        DEPLOYER,
        KeyManager,
        Vault,
        StateChainGateway,
        FLIP,
        DeployerContract,
        AddressChecker,
        os.environ,
    )


def bridge_usdc(fuji_to_goerli, depositor, mint_recipient_address):
    # The contract pointers below will fail if we are in the wrong network.
    if fuji_to_goerli == "1":
        # FUJI TO GOERLI
        usdc = Token.at(USDC_FUJI_ADDRESS)
        token_messenger_cctp = ITokenMessengerMock(TOKENMESSENGER_CCTP_FUJI_ADDRESS)
        destination_domain = ETH_DESTINATION_DOMAIN
        egress_token_messenger_cctp = TOKENMESSENGER_CCTP_GOERLI_ADDRESS

    else:
        # GOERLI to FUJI
        usdc = Token.at(USDC_GOERLI_ADDRESS)
        token_messenger_cctp = ITokenMessengerMock(TOKENMESSENGER_CCTP_GOERLI_ADDRESS)
        destination_domain = FUJI_DESTINATION_DOMAIN
        egress_token_messenger_cctp = TOKENMESSENGER_CCTP_FUJI_ADDRESS

    # Obtain a bytes32 stringified address
    recipient_address_bytes32 = hexStr(to_bytes(mint_recipient_address, "bytes32"))

    egress_minter = input(
        "Input the address that shall do the USDC mint on the egress chain in format '0x...'. Just press enter to allow any address to mint : "
    )
    if egress_minter == "":
        egress_minter = "0x0"
        fcn = token_messenger_cctp.depositForBurn
        args = (
            tokens_to_transfer,
            destination_domain,
            recipient_address_bytes32,
            usdc.address,
        )
    else:
        # Convert address to bytes32
        egress_minter = hexStr(to_bytes(egress_minter, "bytes32"))
        fcn = token_messenger_cctp.depositForBurnWithCaller
        args = (
            tokens_to_transfer,
            destination_domain,
            recipient_address_bytes32,
            usdc.address,
            egress_minter,
        )

    # Check that we have the funds
    assert usdc.balanceOf(DEPLOYER) + usdc.balanceOf(depositor) >= tokens_to_transfer

    # If we want to send to tokens via the Vault, first fund it.
    if depositor != DEPLOYER:
        squid_multicall = SQUID_MULTICALL_ADDRESS

        # Do this to ensure the depositor is a Vault if it's not the EOA
        vault = Vault.at(depositor)
        keyManager_address = vault.getKeyManager()
        ini_usdc_bals = usdc.balanceOf(vault.address)
        if ini_usdc_bals < tokens_to_transfer:
            usdc.transfer(
                vault.address,
                tokens_to_transfer - ini_usdc_bals,
                {"from": DEPLOYER, "required_confs": 1},
            )
        # Commenting it out as might fail if not enough time has passed since transfer
        # so probably the node hasn't updated the balance yet.
        # assert usdc.balanceOf(vault.address) >= tokens_to_transfer

        # Doing it through the Vault means we need to encode the calldata
        keyManager = KeyManager.at(keyManager_address)
        syncNonce(keyManager)

        call0 = [
            0,
            usdc.address,
            0,
            usdc.approve.encode_input(token_messenger_cctp.address, tokens_to_transfer),
            0,
        ]
        call1 = [0, token_messenger_cctp.address, 0, fcn.encode_input(*args), 0]

        calls = [call0, call1]

        args = [usdc, tokens_to_transfer, squid_multicall, calls]

        tx = signed_call(
            keyManager,
            vault.executeActions,
            AGG_SIGNER_1,
            DEPLOYER,
            *args,
        )

        ## If done through Squid, the depositor of the USDC becomes the Multicall
        depositor = squid_multicall

    else:
        ini_usdc_bals = usdc.balanceOf(DEPLOYER)

        # If we are using the EOA, we need to approve the TokenMessengerCCTP
        usdc.approve(
            token_messenger_cctp,
            tokens_to_transfer,
            {"from": DEPLOYER, "required_confs": 1},
        )
        tx = fcn(
            *args,
            {"from": DEPLOYER},
        )
        assert usdc.balanceOf(DEPLOYER) == ini_usdc_bals - tokens_to_transfer

    # Check DepositForBurn event
    assert tx.events["DepositForBurn"]["nonce"] != 0
    assert tx.events["DepositForBurn"]["burnToken"] == usdc
    assert tx.events["DepositForBurn"]["amount"] == tokens_to_transfer
    assert tx.events["DepositForBurn"]["depositor"] == depositor
    assert tx.events["DepositForBurn"]["mintRecipient"] == recipient_address_bytes32
    assert tx.events["DepositForBurn"]["destinationDomain"] == destination_domain
    assert (
        tx.events["DepositForBurn"]["destinationTokenMessenger"]
        == egress_token_messenger_cctp
    )
    # It will be empty (zeros) if not specified
    assert tx.events["DepositForBurn"]["destinationCaller"] == egress_minter
    assert tx.events["MessageSent"]["message"] != JUNK_HEX

    nonce = tx.events["DepositForBurn"]["nonce"]
    message = tx.events["MessageSent"]["message"]
    messageHash = web3.solidityKeccak(["bytes"], [message]).hex()
    mint_recipient = tx.events["DepositForBurn"]["mintRecipient"]
    destination_caller = tx.events["DepositForBurn"]["destinationCaller"]
    tx.info()

    print("Message: ", message)
    print("Message hash: ", messageHash)
    print("Nonce: ", nonce)
    print("Mint recipient: ", mint_recipient)
    print("destinationDomain: ", destination_domain)
    print("destination_caller: ", destination_caller)


def bridge_aUsdc(fuji_to_goerli, depositor, mint_recipient_address):
    # The contract pointers below will fail if we are in the wrong network.
    if fuji_to_goerli == "1":
        # FUJI TO GOERLI
        axelar_gateway = IAxelarGateway(GATEWAY_FUJI_ADDRESS)
        aUsdc = Token.at(aUSDC_FUJI_ADDRESS)
        dst_chain = "ethereum-2"
    else:
        # GOERLI to FUJI - for now not supported
        axelar_gateway = IAxelarGateway(GATEWAY_GOERLI_ADDRESS)
        aUsdc = Token.at(aUSDC_GOERLI_ADDRESS)
        dst_chain = "Avalanche"

    fcn = axelar_gateway.sendToken
    args = (
        dst_chain,  ## destination chain name
        mint_recipient_address[
            2:
        ],  ## some destination address. For some reason I have to remove "0x"
        "aUSDC",  ## asset symbol
        tokens_to_transfer,  ## amount (in atomic units)
    )

    # If we want to send to tokens via the Vault, first fund it.
    if depositor != DEPLOYER:
        squid_multicall = SQUID_MULTICALL_ADDRESS

        # Do this to ensure the depositor is a Vault if it's not the EOA
        vault = Vault.at(depositor)
        keyManager_address = vault.getKeyManager()
        ini_aUsdc_bals = aUsdc.balanceOf(vault.address)
        if ini_aUsdc_bals < tokens_to_transfer:
            aUsdc.transfer(
                vault.address,
                tokens_to_transfer - ini_aUsdc_bals,
                {"from": DEPLOYER, "required_confs": 1},
            )
        # Doing it through the Vault means we need to encode the calldata
        keyManager = KeyManager.at(keyManager_address)
        syncNonce(keyManager)

        call0 = [
            0,
            aUsdc.address,
            0,
            aUsdc.approve.encode_input(axelar_gateway.address, tokens_to_transfer),
            0,
        ]
        call1 = [0, axelar_gateway.address, 0, fcn.encode_input(*args), 0]

        calls = [call0, call1]

        args = [aUsdc, tokens_to_transfer, squid_multicall, calls]

        tx = signed_call(
            keyManager,
            vault.executeActions,
            AGG_SIGNER_1,
            DEPLOYER,
            *args,
        )

        ## If done through Squid, the depositor of the USDC becomes the Multicall
        depositor = squid_multicall

    else:
        # Make a transfer from FUJI-EOA to an Address in Goerli. For now we don't
        # use Squid to call Vault's swap function. Instead we send it to a Deposit and
        # then fetch it with the Vault via deployAndFetch or via fetch.
        aUsdc.approve(
            axelar_gateway.address,
            tokens_to_transfer,
            {"from": DEPLOYER, "required_confs": 1},
        )

        # This will automatically mint the tokens on the other chain. On testnet they don't seem to
        # support USDC transfers, only aUSDC. Real network should also support USDC. Otherwise we need
        # to use Squid on top of it. But we want USDC in the auxiliary chain.
        tx = fcn(
            *args,
            {"from": DEPLOYER, "required_confs": 1},
        )

    tx.info()
    print(
        f"Success! aUSDC tokens should appear on the egress chain {dst_chain} at address {mint_recipient_address}"
    )


def get_attestation(message):
    message_hash = web3.solidityKeccak(["bytes"], [message]).hex()

    attestation_response = {"status": "pending"}
    while attestation_response["status"] != "complete":
        response = requests.get(
            f"https://iris-api-sandbox.circle.com/attestations/{message_hash}"
        )
        attestation_response = json.loads(response.text)

        # In case of error this returns {'error': 'Message hash not found'}
        if "error" in attestation_response:
            sys.exit("Failed to get the attestation from the message provided")
        # When success it returns: {'status': ... , 'attestation': ...}
        elif attestation_response["status"] == "complete":
            break
        else:
            time.sleep(2)

    print(attestation_response)
    return attestation_response["attestation"]


def get_and_submit_attestation(
    message, fuji_to_goerli, depositor, mint_recipient_address
):

    attestation_response = get_attestation(message)

    if fuji_to_goerli == "1":
        message_transmitter_cctp = IMessageTransmitterMock(
            MESSAGE_TRANSMITTER_CCTP_GOERLI
        )
        source_domain = FUJI_DESTINATION_DOMAIN
        usdc_address = USDC_GOERLI_ADDRESS
        source_token_messenger = TOKENMESSENGER_CCTP_FUJI_ADDRESS
    else:
        message_transmitter_cctp = IMessageTransmitterMock(
            MESSAGE_TRANSMITTER_CCTP_FUJI
        )
        source_domain = ETH_DESTINATION_DOMAIN
        usdc_address = USDC_FUJI_ADDRESS
        source_token_messenger = TOKENMESSENGER_CCTP_GOERLI_ADDRESS

    sender_bytes32 = hexStr(to_bytes(source_token_messenger, "bytes32"))

    # Ask user for extra parameters for validation sender (original sender in the src chain)
    # nonce (in the source chain) not sure what messageBody is.
    usdc_contract = Token.at(usdc_address)
    ini_usdc_bals = usdc_contract.balanceOf(mint_recipient_address)

    expected_nonce = input("Enter expected nonce: ")

    # We assume that if depositor != DEPLOYER then it's the Vault contract
    if depositor != DEPLOYER:
        squid_multicall = SQUID_MULTICALL_ADDRESS
        # Most likely when going through the Vault depositor ==
        vault = Vault.at(depositor)
        keyManager_address = vault.getKeyManager()

        keyManager = KeyManager.at(keyManager_address)
        syncNonce(keyManager)

        # Doing it through the Vault means we need to encode the calldata

        calls = [
            [
                0,
                message_transmitter_cctp.address,
                0,
                message_transmitter_cctp.receiveMessage.encode_input(
                    message, attestation_response
                ),
                0,
            ]
        ]

        args = ["0x0000000000000000000000000000000000000000", 0, squid_multicall, calls]

        tx = signed_call(
            keyManager,
            vault.executeActions,
            AGG_SIGNER_1,
            DEPLOYER,
            *args,
        )

        ## If done through Squid, the depositor of the USDC becomes the Multicall
        depositor = squid_multicall
    else:
        tx = message_transmitter_cctp.receiveMessage(
            message, attestation_response, {"from": DEPLOYER}
        )

    tx.info()
    print("Attestation succesfully submitted!")
    print("Checking values")

    assert (
        usdc_contract.balanceOf(mint_recipient_address)
        == ini_usdc_bals + tokens_to_transfer
    )

    assert tx.events["MessageReceived"]["caller"] == depositor
    assert tx.events["MessageReceived"]["sourceDomain"] == source_domain
    assert tx.events["MessageReceived"]["nonce"] == expected_nonce
    assert tx.events["MessageReceived"]["sender"] == sender_bytes32
    assert tx.events["MessageReceived"]["messageBody"] != "0x0"
    assert tx.events["MintAndWithdraw"]["mintRecipient"] == mint_recipient_address
    assert tx.events["MintAndWithdraw"]["amount"] == tokens_to_transfer
    assert tx.events["MintAndWithdraw"]["mintToken"] == usdc_address

    print("Values are correct! Success!")

    return tx
