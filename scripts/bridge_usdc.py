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
    AxelarGatewayMock,
    AxelarGasService,
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
        syncNonce(keyManager_address)

        calldata0 = usdc.approve.encode_input(
            token_messenger_cctp.address, tokens_to_transfer
        )
        calldata1 = fcn.encode_input(*args)

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
        axelar_gateway = AxelarGatewayMock.at(GATEWAY_FUJI_ADDRESS)
        aUsdc = Token.at(aUSDC_FUJI_ADDRESS)
        dst_chain = "ethereum-2"
        # axelar_gas_service = AxelarGasService.at(GAS_SERVICE_FUJI_ADDRESS)
    else:
        # GOERLI to FUJI - for now not supported
        axelar_gateway = AxelarGatewayMock.at(GATEWAY_GOERLI_ADDRESS)
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
        # Do this to ensure the depositor is a Vault if it's not the EOA
        vault = Vault.at(depositor)
        keyManager_address = vault.getKeyManager()
        ini_usdc_bals = aUsdc.balanceOf(vault.address)
        if ini_usdc_bals < tokens_to_transfer:
            aUsdc.transfer(
                vault.address,
                tokens_to_transfer - ini_usdc_bals,
                {"from": DEPLOYER, "required_confs": 1},
            )
        # Doing it through the Vault means we need to encode the calldata
        syncNonce(keyManager_address)

        calldata0 = aUsdc.approve.encode_input(
            axelar_gateway.address, tokens_to_transfer
        )
        calldata1 = fcn.encode_input(*args)

        args = [[aUsdc, 0, calldata0], [axelar_gateway, 0, calldata1]]
        callDataNoSig = vault.executeActions.encode_input(
            agg_null_sig(keyManager_address, chain.id), args
        )
        tx = vault.executeActions(
            AGG_SIGNER_1.getSigData(callDataNoSig, keyManager_address),
            args,
            {"from": DEPLOYER},
        )

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

    # We assume that if depositor != DEPLOYER then it's the Vault contract
    if depositor != DEPLOYER:
        # Most likely when going through the Vault depositor ==
        vault = Vault.at(depositor)
        keyManager_address = vault.getKeyManager()

        # Doing it through the Vault means we need to encode the calldata
        calldata = message_transmitter_cctp.receiveMessage.encode_input(
            message, attestation_response
        )
        args = [[message_transmitter_cctp, 0, calldata]]

        syncNonce(keyManager_address)

        callDataNoSig = vault.executeActions.encode_input(
            agg_null_sig(keyManager_address, chain.id), args
        )
        # Get the latest used nonce, as this is not synched
        tx = vault.executeActions(
            AGG_SIGNER_1.getSigData(
                callDataNoSig,
                keyManager_address,
            ),
            args,
            {"from": DEPLOYER},
        )

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


# The deployed contract might have already signed some messages, so we need to sync the nonce
# of the contract with the nonces in consts.py used to signed the messages.
def syncNonce(keyManager_address):
    keyManager = KeyManager.at(keyManager_address)
    while keyManager.isNonceUsedByAggKey(nonces[AGG]) != False:
        nonces[AGG] += 1

    print("Synched Nonce: ", nonces[AGG])
    return nonces


# def axelar_and_squid():
#         SQUID_GOERLI_ADDRESS = "0xe25e5ae59592bFbA3b5359000fb72E6c21D3228E"
#         # This second action is to mimic the case where we want to ingress from a chain we don't support and we
#         # need either Squid to transfer to a Deposit (that should be easy to do) or we want Squid to call SwapToken
#         # or swapNative and pass the xswap information to the Vault. It should work no problem even though it's quite
#         # a hustle to set up.

#         # TODO: This is failing on the egress side for some reason. Also, the gas is not being witnessed, it might
#         # need to be part of the same contract.
#         # Try to do it via SimpleCallContract.send() to see if it picks up the gas and if it works. Otherwise we can
#         # just let it go and assume that this is feasible using Squid.

#         aUsdc.approve(
#             axelar_gateway.address,
#             tokens_to_transfer,
#             {"from": DEPLOYER, "required_confs": 1},
#         )

#         # Encoded payayload calltype (Default=0) + refundRecipient
#         # payload = "0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000037876b47dee43492dac3d87f7682df52ddbc65ca"
#         # payload all zeroos
#         payload = "0x000000000000000000000000000000000000000000000000000000000000004000000000000000000000000037876b47dee43492dac3d87f7682df52ddbc65ca0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000"
#         axelar_gas_service.payNativeGasForContractCallWithToken(
#             DEPLOYER,
#             "ethereum-2",
#             SQUID_GOERLI_ADDRESS[2:],
#             payload,
#             "aUSDC",
#             tokens_to_transfer,
#             DEPLOYER,
#             {"from": DEPLOYER, "value": 1 * 10**18, "required_confs": 1},
#         )
#         print(error_from_string("BurnFailed(string)"))

#         # We try to send the aUSDC to AXLR, then to Squid on the egress chain and then so it calls the Vault
#         tx = axelar_gateway.callContractWithToken(
#             "ethereum-2",  ## destination chain name
#             SQUID_GOERLI_ADDRESS[2:],  ## some destination address (should be your own)
#             payload,  ## message
#             "aUSDC",  ## asset symbol
#             tokens_to_transfer,  ## amount (in atomic units)
#             {"from": DEPLOYER, "required_confs": 1},
#         )

#         tx.info()