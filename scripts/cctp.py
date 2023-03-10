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


# def avax_to_eth():
#     # Test AVAX to ETH
#     # user_address = "0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca"
#     # This user address should have some AVAX and USDC

#     tokenMessengerCCTP_avax_address = "0xeb08f243e5d3fcff26a9e38ae5520a669f4019d0"

#     tokensToTransfer = 1 * 10**6
#     ETH_DESTINATION_DOMAIN = 0
#     deployedVaultGoerli = "0x123"
#     USDC_AVAX_CONTRACT_ADDRESS = "0x5425890298aed601595a70AB815c96711a31Bc65"
#     tokenMessengerCCTP_goerli = "0xd0c3da58f55358142b8d3e06c1c30c5c6114efe8"

#     usdc_avax = Token.at(USDC_AVAX_CONTRACT_ADDRESS)
#     # assert(cf.safekeeper == "0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca")
#     print(usdc_avax.balanceOf("0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca"))
#     print(tokensToTransfer)

#     usdc_avax.approve(
#         tokenMessengerCCTP_avax_address, tokensToTransfer, {"from": DEPLOYER}
#     )

#     # Make a call from an EOA to the Circle contract and get the messageHash
#     tokenMessengerCCTP_avax = TokenMessengerMock.at(tokenMessengerCCTP_avax_address)
#     tx = tokenMessengerCCTP_avax.depositForBurn(
#         tokensToTransfer,
#         ETH_DESTINATION_DOMAIN,
#         deployedVaultGoerli,
#         USDC_AVAX_CONTRACT_ADDRESS,
#         {"from": DEPLOYER},
#     )

#     # Check DepositForBurn event
#     assert tx.events["DepositForBurn"]["nonce"] != 0
#     assert tx.events["DepositForBurn"]["burnToken"] == USDC_AVAX_CONTRACT_ADDRESS
#     assert tx.events["DepositForBurn"]["amount"] == tokensToTransfer
#     assert tx.events["DepositForBurn"]["depositor"] == DEPLOYER
#     assert tx.events["DepositForBurn"]["mintRecipient"] == deployedVaultGoerli
#     assert tx.events["DepositForBurn"]["destinationDomain"] == ETH_DESTINATION_DOMAIN
#     assert (
#         tx.events["DepositForBurn"]["destinationTokenMessenger"]
#         == tokenMessengerCCTP_goerli
#     )
#     assert tx.events["DepositForBurn"]["destinationCaller"] == "0x0"

#     assert tx.events["MessageSent"]["message"] != "0x1234"

#     message = tx.events["MessageSent"]["message"]
#     messageHash = web3.keccak(message)

#     print("message: ", message)
#     print("messageHash: ", messageHash)

#     # We can now fetch the attestation from cirleci. We probably do this in different functions
#     # with a real attestation.
#     # fetch(`https://iris-api-sandbox.circle.com/attestations/${messageHash}`);


# def eth_to_avax():

#     cf = deploy_set_Chainflip_contracts(
#         DEPLOYER, KeyManager, Vault, StakeManager, FLIP, os.environ
#     )

#     # Check we are in a Goerli fork
#     # print(web3.eth.get_balance("0xc6e2459991BfE27cca6d86722F35da23A1E4Cb97"))
#     # print(web3.eth.get_balance("0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca"))

#     ## Fund the Vault with our initial USDC
#     # user_address = "0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca"
#     # This user address should have some AVAX and USDC

#     usdc_goerli = Token.at("0x07865c6e87b9f70255377e024ace6630c1eaa37f")

#     print("DEPLOYER: ", DEPLOYER)

#     # We have a balance of 10*10**6
#     # We force the transaction to be sent by the user but in reality we would
#     # need to intput the SEED and sign it from there.
#     initialBalance = usdc_goerli.balanceOf(DEPLOYER)
#     tokensToTransfer = 1 * 10**6
#     assert initialBalance > tokensToTransfer
#     usdc_goerli.transfer(cf.vault.address, tokensToTransfer, {"from": DEPLOYER})

#     assert usdc_goerli.balanceOf(cf.vault.address) == tokensToTransfer
#     assert usdc_goerli.balanceOf(DEPLOYER) == initialBalance - tokensToTransfer

#     # Craft a transaction to the CCTP address. For now using this instead of Brownie
#     # encode_input because I want to avoid needing the contract here.
#     tokenMessengerCCTP_goerli = TokenMessengerMock.at(
#         "0xd0c3da58f55358142b8d3e06c1c30c5c6114efe8"
#     )
#     tokenMessengerCCTP_avax_address = "0xeb08f243e5d3fcff26a9e38ae5520a669f4019d0"

#     calldata0 = usdc_goerli.approve.encode_input(
#         tokenMessengerCCTP_goerli.address, tokensToTransfer
#     )
#     AVAX_DESTINATION_DOMAIN = 1
#     destinationAddressInBytes32 = JUNK_HEX
#     USDC_ETH_CONTRACT_ADDRESS = usdc_goerli
#     calldata1 = tokenMessengerCCTP_goerli.depositForBurn.encode_input(
#         tokensToTransfer,
#         AVAX_DESTINATION_DOMAIN,
#         destinationAddressInBytes32,
#         USDC_ETH_CONTRACT_ADDRESS,
#     )

#     args = [[usdc_goerli, 0, calldata0], [tokenMessengerCCTP_goerli, 0, calldata1]]
#     callDataNoSig = cf.vault.executeActions.encode_input(
#         agg_null_sig(cf.keyManager.address, chain.id), args
#     )
#     tx = cf.vault.executeActions(
#         AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
#         args,
#         {"from": DEPLOYER},
#     )

#     assert usdc_goerli.balanceOf(cf.vault.address) == 0

#     print("Interacting address: ", tokenMessengerCCTP_goerli)

#     # Check DepositForBurn event
#     assert tx.events["DepositForBurn"]["nonce"] != 0
#     assert tx.events["DepositForBurn"]["burnToken"] == usdc_goerli
#     assert tx.events["DepositForBurn"]["amount"] == tokensToTransfer
#     assert tx.events["DepositForBurn"]["depositor"] == cf.vault.address
#     assert tx.events["DepositForBurn"]["mintRecipient"] == destinationAddressInBytes32
#     assert tx.events["DepositForBurn"]["destinationDomain"] == AVAX_DESTINATION_DOMAIN
#     assert (
#         tx.events["DepositForBurn"]["destinationTokenMessenger"]
#         == tokenMessengerCCTP_avax_address
#     )
#     assert tx.events["DepositForBurn"]["destinationCaller"] == "0x0"

#     assert tx.events["MessageSent"]["message"] != JUNK_HEX

#     message = tx.events["MessageSent"]["message"]
#     messageHash = web3.solidityKeccak(["bytes"], [message]).hex()


def get_attestation(message):
    message_hash = web3.solidityKeccak(["bytes"], [message]).hex()
    # messageHash = "0xc9ac14d7c51d474215d3c01e024926d23c79a34816ecdc2cb81f685c1b1a1fbc"

    attestation_response = {"status": "pending"}
    while attestation_response["status"] != "complete":
        response = requests.get(
            f"https://iris-api-sandbox.circle.com/attestations/{message_hash}"
        )
        attestation_response = json.loads(response.text)
        time.sleep(2)

    # attestation_response = {'status': ... , 'attestation': ...}
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
    else:
        message_transmitter_cctp = MessageTransmitter.at(MESSAGE_TRANSMITTER_CCTP_FUJI)
        source_domain = ETH_DESTINATION_DOMAIN
        usdc_address = USDC_FUJI_ADDRESS

    # Ask user for extra parameters for validation sender (original sender in the src chain)
    # nonce (in the source chain) not sure what messageBody is.
    usdc_contract = Token.at(usdc_address)
    ini_usdc_bals = usdc_contract.balanceOf(mint_recipient_address)

    expected_nonce = input("Enter expected nonce: ")
    sender_ingress_chain = input(
        "Enter the sender in the ingress chain as an address: "
    )
    sender_bytes32 = hexStr(to_bytes(sender_ingress_chain, "bytes32"))

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
