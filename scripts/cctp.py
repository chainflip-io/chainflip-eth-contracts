import sys
import os
import json

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import (
    accounts,
    Token,
    TokenMessengerMock,
    network,
    MessageTransmitter,
    KeyManager,
    Vault,
    StakeManager,
    FLIP,
)
from deploy import deploy_set_Chainflip_contracts
from brownie.convert import to_bytes

import requests
import time

# NOTE: When forking a network (in another terminal) it spins a copy of the network
# with the default hardhat chain id 31337. Another option is to declare the network
# in hardhat.config.js, but we would need to add that manually as all the networks
# that we support are via brownie. Then brownie might not play well with that.
# Therefore we just spin the forks in another terminal via hardhat command.

# Valid for Goerli
# message = "0x000000000000000100000000000000000000a01b000000000000000000000000eb08f243e5d3fcff26a9e38ae5520a669f4019d0000000000000000000000000d0c3da58f55358142b8d3e06c1c30c5c6114efe80000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000005425890298aed601595a70ab815c96711a31bc65000000000000000000000000000000000000000000000000000000000000012300000000000000000000000000000000000000000000000000000000000f424000000000000000000000000037876b47dee43492dac3d87f7682df52ddbc65ca"
# messageHash = "0xc9ac14d7c51d474215d3c01e024926d23c79a34816ecdc2cb81f685c1b1a1fbc"
# For the above message, this is the correct attestation
# attestation_response['attestation'] = '0x5c858ef0d057a12a309ddbe682d138f00ceae129377edc48b3e7cf050d74b34413729de6ce81fb05ceb3cdb50e689754d02134295fe84ff4d3e06df58f4a59751bf44e0efd9e56c7de548a98e95bc06995cd0fd3fb539bb13362230430e26944210d797913e10ca73d4814beba039a8f2328f806fffa4b9cea95f8e0e71aee4dab1c'

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

# Goerli
TOKENMESSENGER_CCTP_GOERLI_ADDRESS = "0xd0c3da58f55358142b8d3e06c1c30c5c6114efe8"
USDC_GOERLI_ADDRESS = "0x07865c6e87b9f70255377e024ace6630c1eaa37f"
MESSAGE_TRANSMITTER_CCTP_GOERLI = "0x26413e8157cd32011e726065a5462e97dd4d03d9"
FUJI_DESTINATION_DOMAIN = 1

# Bridging properties
tokens_to_transfer = 1 * 10**6


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

# TODO: Think about adding an option or a function to do the whole flow in actual testnets (not forks)
# for a complete atomic test.


def main():
    print("Starting cctp script")

    print(f"Chain ID: {chain.id}")

    action = input(
        "What do you want to do? [1] Bridge USDC Source chain [2] Get Attestation [3] Get & Submit attestation on egress chain: "
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
            bridge_usdc(fuji_to_goerli, depositor, mint_recipient_address)
        elif action == "3":
            message = input(
                "We will get the attestation and submit it. Input the message emitted in the source chain in format '0x...' : "
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
    return deploy_set_Chainflip_contracts(
        DEPLOYER, KeyManager, Vault, StakeManager, FLIP, os.environ
    )


def bridge_usdc(fuji_to_goerli, depositor, mint_recipient_address):
    # The contract pointers below will fail if we are in the wrong network.
    if fuji_to_goerli == "1":
        # FUJI TO GOERLI
        usdc = Token.at(USDC_FUJI_ADDRESS)
        token_messenger_cctp = TokenMessengerMock.at(TOKENMESSENGER_CCTP_FUJI_ADDRESS)
        destination_domain = ETH_DESTINATION_DOMAIN
        egress_token_messenger_cctp = TOKENMESSENGER_CCTP_GOERLI_ADDRESS
    else:
        # GOERLI to FUJI
        usdc = Token.at(USDC_GOERLI_ADDRESS)
        token_messenger_cctp = TokenMessengerMock.at(TOKENMESSENGER_CCTP_GOERLI_ADDRESS)
        destination_domain = FUJI_DESTINATION_DOMAIN
        egress_token_messenger_cctp = TOKENMESSENGER_CCTP_FUJI_ADDRESS

    # Obtain a bytes32 stringified address
    recipient_address_bytes32 = hexStr(to_bytes(mint_recipient_address, "bytes32"))

    # TODO: Add input here for a particular destination_caller

    # Check that we have the funds
    assert usdc.balanceOf(DEPLOYER) + usdc.balanceOf(depositor) >= tokens_to_transfer

    # If we want to send to tokens via the Vault, first fund it.
    if depositor != DEPLOYER:
        # Do this to ensure the depositor is a Vault if it's not the EOA
        vault = Vault.at(depositor)
        keyManager_address = vault.getKeyManager()
        ini_usdc_bals = usdc.balanceOf(vault.address)
        if ini_usdc_bals < tokens_to_transfer:
            usdc.transfer(
                vault.address, tokens_to_transfer - ini_usdc_bals, {"from": DEPLOYER}
            )
        assert usdc.balanceOf(vault.address) >= tokens_to_transfer

        # Doing it through the Vault means we need to encode the calldata
        calldata0 = usdc.approve.encode_input(
            token_messenger_cctp.address, tokens_to_transfer
        )
        calldata1 = token_messenger_cctp.depositForBurn.encode_input(
            tokens_to_transfer,
            destination_domain,
            recipient_address_bytes32,
            usdc.address,
        )

        args = [[usdc, 0, calldata0], [token_messenger_cctp, 0, calldata1]]
        callDataNoSig = vault.executeActions.encode_input(
            agg_null_sig(keyManager_address, chain.id), args
        )
        tx = vault.executeActions(
            AGG_SIGNER_1.getSigData(callDataNoSig, keyManager_address),
            args,
            {"from": DEPLOYER},
        )

    else:
        # If we are using the EOA, we need to approve the TokenMessengerCCTP
        usdc.approve(token_messenger_cctp, tokens_to_transfer, {"from": DEPLOYER})
        tx = token_messenger_cctp.depositForBurn(
            tokens_to_transfer,
            destination_domain,
            recipient_address_bytes32,
            usdc.address,
            {"from": DEPLOYER},
        )

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
    # No destination caller.
    # TODO: We should try with depositForBurnWithCaller later so only a certain address
    # can mint on the egress chain (EOA or Vault)
    assert tx.events["DepositForBurn"]["destinationCaller"] == "0x0"
    assert tx.events["MessageSent"]["message"] != JUNK_HEX

    nonce = tx.events["DepositForBurn"]["nonce"]
    message = tx.events["MessageSent"]["message"]
    messageHash = web3.solidityKeccak(["bytes"], [message]).hex()
    mint_recipient = tx.events["DepositForBurn"]["mintRecipient"]
    destination_caller = tx.events["DepositForBurn"]["destinationCaller"]

    print("Message: ", message)
    print("Message hash: ", messageHash)
    print("Nonce: ", nonce)
    print("Mint recipient: ", mint_recipient)
    print("destinationDomain: ", destination_domain)
    print("destination_caller: ", destination_caller)


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
        message_transmitter_cctp = MessageTransmitter.at(
            MESSAGE_TRANSMITTER_CCTP_GOERLI
        )
        source_domain = FUJI_DESTINATION_DOMAIN
        usdc_address = USDC_GOERLI_ADDRESS
        source_token_messenger = TOKENMESSENGER_CCTP_FUJI_ADDRESS
    else:
        message_transmitter_cctp = MessageTransmitter.at(MESSAGE_TRANSMITTER_CCTP_FUJI)
        source_domain = ETH_DESTINATION_DOMAIN
        usdc_address = USDC_FUJI_ADDRESS
        source_token_messenger = TOKENMESSENGER_CCTP_GOERLI_ADDRESS

    sender_bytes32 = hexStr(to_bytes(source_token_messenger, "bytes32"))

    # Ask user for extra parameters for validation sender (original sender in the src chain)
    # nonce (in the source chain) not sure what messageBody is.
    usdc_contract = Token.at(usdc_address)
    ini_usdc_bals = usdc_contract.balanceOf(mint_recipient_address)

    expected_nonce = input("Enter expected nonce: ")

    tx = message_transmitter_cctp.receiveMessage(
        message, attestation_response, {"from": depositor}
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
