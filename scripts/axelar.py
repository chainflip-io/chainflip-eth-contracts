import sys
import os
import json


sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import (
    accounts,
    Token,
    network,
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

AUTONOMY_SEED = os.environ["SEED"]
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
print(f"DEPLOYER = {DEPLOYER}")

# Set the priority fee for all transactions
network.priority_fee("1 gwei")

# assert chain.id in [
#     31337,
#     43113,
#     5,
# ], "This script is only for AVAX, Goerli and hardhat forks"

## Addresses in AVAX-Test (FUJI) and goerli
# FUJI
USDC_FUJI_ADDRESS = "0x5425890298aed601595a70AB815c96711a31Bc65"
aUSDC_FUJI_ADDRESS = "0x57F1c63497AEe0bE305B8852b354CEc793da43bB"
GATEWAY_FUJI_ADDRESS = "0xC249632c2D40b9001FE907806902f63038B737Ab"
GAS_SERVICE_FUJI_ADDRESS = "0xbE406F0189A0B4cf3A05C286473D23791Dd44Cc6"

# # Goerli
# TOKENMESSENGER_CCTP_GOERLI_ADDRESS = "0xd0c3da58f55358142b8d3e06c1c30c5c6114efe8"
# USDC_GOERLI_ADDRESS = "0x07865c6e87b9f70255377e024ace6630c1eaa37f"
SQUID_GOERLI_ADDRESS = "0xe25e5ae59592bFbA3b5359000fb72E6c21D3228E"

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

# TODO: Idea here is to try ingressing funds from non-supporte chain to a supported chain. This is done
# via Axelar to either an ingressAddress (no CCM) or to the Vault (with CCM). We do FUJI to Goerli.


def main():
    print("Starting Axelar script")

    print(f"Chain ID: {chain.id}")

    print(
        "Bridging from current chain from EOA (user) to the other chain, which is CF supported"
    )

    try:
        axelar_gateway = AxelarGatewayMock.at(GATEWAY_FUJI_ADDRESS)
        axelar_gas_service = AxelarGasService.at(GAS_SERVICE_FUJI_ADDRESS)
        # Add squid if we need to
    except:
        print("Wrong chain. Please connect to FUJI or hardhat fork of FUJI")

    action = input(
        "Send aUSDC from Fuji to Goerli address: [1] To an address [2] To the vault with CCM : "
    )

    aUsdc = Token.at(aUSDC_FUJI_ADDRESS)

    if action == "1":
        # Make a transfer from FUJI-EOA to a Deposit Address in Goerli. Then fetch it with the Vault via
        # deployAndFetch or via fetch.

        aUsdc.approve(
            axelar_gateway.address,
            tokens_to_transfer,
            {"from": DEPLOYER, "required_confs": 1},
        )

        # This will automatically mint the tokens on the other chain. On testnet they don't seem to
        # support USDC transfers, only aUSDC. Real network should also support USDC. Otherwise we need
        # to use Squid on top of it. But we want USDC in the auxiliary chain.
        tx = axelar_gateway.sendToken(
            "ethereum-2",  ## destination chain name
            "37876B47DEE43492DAC3d87F7682df52dDBC65Ca",  ## some destination address (should be your own)
            "aUSDC",  ## asset symbol
            tokens_to_transfer,  ## amount (in atomic units)
            {"from": DEPLOYER, "required_confs": 1},
        )
        tx.info()
    elif action == "2":
        aUsdc.approve(
            axelar_gateway.address,
            tokens_to_transfer,
            {"from": DEPLOYER, "required_confs": 1},
        )

        # TODO: This is failing on the egress side for some reason. Also, the gas is not being witnessed, it might
        # need to be part of the same contract.
        # Try to do it via SimpleCallContract.send() to see if it picks up the gas and if it works. Otherwise we can
        # just let it go and assume that this is feasible using Squid.

        # Encoded payayload calltype (Default=0) + refundRecipient
        # payload = "0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000037876b47dee43492dac3d87f7682df52ddbc65ca"
        # payload all zeroos
        payload = "0x000000000000000000000000000000000000000000000000000000000000004000000000000000000000000037876b47dee43492dac3d87f7682df52ddbc65ca0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000"
        axelar_gas_service.payNativeGasForContractCallWithToken(
            DEPLOYER,
            "ethereum-2",
            SQUID_GOERLI_ADDRESS[2:],
            payload,
            "aUSDC",
            tokens_to_transfer,
            DEPLOYER,
            {"from": DEPLOYER, "value": 1 * 10**18, "required_confs": 1},
        )
        print(error_from_string("BurnFailed(string)"))

        # We try to send the aUSDC to AXLR, then to Squid on the egress chain and then so it calls the Vault
        tx = axelar_gateway.callContractWithToken(
            "ethereum-2",  ## destination chain name
            SQUID_GOERLI_ADDRESS[2:],  ## some destination address (should be your own)
            payload,  ## message
            "aUSDC",  ## asset symbol
            tokens_to_transfer,  ## amount (in atomic units)
            {"from": DEPLOYER, "required_confs": 1},
        )

        tx.info()


def error_from_string(string):
    return "typed error: " + web3.keccak(text=string)[:4].hex()


def getMainnetTokenAddresses():
    axelar_gateway = AxelarGatewayMock.at("0x5029C0EFf6C34351a0CEc334542cDb22c7928f78")
    print(axelar_gateway.tokenAddresses("axlUSDC"))
    print(axelar_gateway.tokenAddresses("USDC"))
