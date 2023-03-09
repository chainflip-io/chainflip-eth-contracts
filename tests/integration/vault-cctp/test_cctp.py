from consts import *
import os
from brownie import accounts, network
from utils import *
from shared_tests import *
import pytest

import requests


# TODO: Problem. This takes the brownie accounts by default, so we can't use it on real
# live networks. We are hacking it forcing the {"from": user_address}. We should take the 
# Seed instead and we can set it to JUNK if we want to use the preconfigured accounts.
# Trying to fix that in cctp-x-to-y.py
AUTONOMY_SEED = os.environ["SEED"]
DEPLOY_ARTEFACT_ID = os.environ.get("DEPLOY_ARTEFACT_ID")
cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]


# Only run this tests with a separate terminal running a Goerli fork
# npx hardhat node --fork https://goerli.infura.io/v3/<INFURA_API>
# That seems to create a chain with id 31337

#  Running it automatically will fail, as this accounts are specific to Forked Goerli
def test_depositForBurn(cf, Token, TokenMessengerMock):
    
    # Quick workaround to check if we should skip this test because we are not in Goerli
    # Unless we setup the forked network in the conf file, it will have the default
    # hardhat id, so we can't check that.
    try:
        usdc_goerli = Token.at("0x07865c6e87b9f70255377e024ace6630c1eaa37f")
    except:
        pytest.skip("Skipping test because we are not in Goerli or Goerli fork")


    # Check we are in a Goerli fork
    # print(web3.eth.get_balance("0xc6e2459991BfE27cca6d86722F35da23A1E4Cb97"))
    # print(web3.eth.get_balance("0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca"))

    ## Fund the Vault with our initial USDC
    # user_address = "0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca"
    # This user address should have some AVAX and USDC

    usdc_goerli = Token.at("0x07865c6e87b9f70255377e024ace6630c1eaa37f")

    print("DEPLOYER: ", DEPLOYER)

    # We have a balance of 10*10**6
    # We force the transaction to be sent by the user but in reality we would
    # need to intput the SEED and sign it from there.
    initialBalance = usdc_goerli.balanceOf(DEPLOYER)
    assert initialBalance == 10 * 10**6
    tokensToTransfer = 1 * 10**6
    usdc_goerli.transfer(cf.vault.address, tokensToTransfer, {"from": DEPLOYER})

    assert usdc_goerli.balanceOf(cf.vault.address) == tokensToTransfer
    assert usdc_goerli.balanceOf(DEPLOYER) == initialBalance - tokensToTransfer

    # Craft a transaction to the CCTP address. For now using this instead of Brownie
    # encode_input because I want to avoid needing the contract here.
    tokenMessengerCCTP_goerli = TokenMessengerMock.at(
        "0xd0c3da58f55358142b8d3e06c1c30c5c6114efe8"
    )
    tokenMessengerCCTP_avax_address = "0xeb08f243e5d3fcff26a9e38ae5520a669f4019d0"

    calldata0 = usdc_goerli.approve.encode_input(
        tokenMessengerCCTP_goerli.address, tokensToTransfer
    )
    AVAX_DESTINATION_DOMAIN = 1
    destinationAddressInBytes32 = JUNK_HEX
    USDC_ETH_CONTRACT_ADDRESS = usdc_goerli
    calldata1 = tokenMessengerCCTP_goerli.depositForBurn.encode_input(
        tokensToTransfer,
        AVAX_DESTINATION_DOMAIN,
        destinationAddressInBytes32,
        USDC_ETH_CONTRACT_ADDRESS,
    )

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        [[usdc_goerli, 0, calldata0], [tokenMessengerCCTP_goerli, 0, calldata1]],
        sender = DEPLOYER
    )

    assert usdc_goerli.balanceOf(cf.vault.address) == 0

    print("Interacting address: ", tokenMessengerCCTP_goerli)

    # Check DepositForBurn event
    assert tx.events["DepositForBurn"]["nonce"] != 0
    assert tx.events["DepositForBurn"]["burnToken"] == usdc_goerli
    assert tx.events["DepositForBurn"]["amount"] == tokensToTransfer
    assert tx.events["DepositForBurn"]["depositor"] == cf.vault.address
    assert tx.events["DepositForBurn"]["mintRecipient"] == destinationAddressInBytes32
    assert tx.events["DepositForBurn"]["destinationDomain"] == AVAX_DESTINATION_DOMAIN
    assert (
        tx.events["DepositForBurn"]["destinationTokenMessenger"]
        == tokenMessengerCCTP_avax_address
    )
    assert tx.events["DepositForBurn"]["destinationCaller"] == "0x0"

    assert tx.events["MessageSent"]["message"] != JUNK_HEX

    message = tx.events["MessageSent"]["message"]
    messageHash = web3.keccak(message)

    # We can now fetch the attestation from cirleci. We probably do this in different functions
    # with a real attestation.
    # fetch(`https://iris-api-sandbox.circle.com/attestations/${messageHash}`);

    # We need to test we can submit an attestation. How do we do that? Options:
    #     1. We mock that logic in our contract and we call it. This would only be a PoC though.
    #     2. We parse the chain for receiveMessages (attestations) submitted that don't require an owner.
    #           We then fork the chain right before it's submitted and we submitt it ourselves. We won't
    #           get the USDC though, but it proves the logic works.
    #     3. We deploy a real Vault in Goerli that we control. Then we submit an AVAX CCTP call pointing
    #           at our Vault. Then we can always fork the chain at any point, call the Vault and submit
    #           the attestation (assuming they don't get deprecated).
    # OPTION 3 seems like the best!

    # Try out same test but depositForBurnWithCaller

# To run in AVAX or AVAX fork.
# npx hardhat node --fork https://api.avax-test.network/ext/bc/C/rpc
def test_fetch_attestation_from_AVAX(TokenMessengerMock, Token):
    user_address = "0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca"

    tokenMessengerCCTP_avax_address = "0xeb08f243e5d3fcff26a9e38ae5520a669f4019d0"

    tokensToTransfer = 1 * 10**6
    ETH_DESTINATION_DOMAIN = 0
    deployedVaultGoerli = "0x123"
    USDC_AVAX_CONTRACT_ADDRESS = "0x5425890298aed601595a70AB815c96711a31Bc65"
    tokenMessengerCCTP_goerli = "0xd0c3da58f55358142b8d3e06c1c30c5c6114efe8"

    usdc_avax = Token.at(USDC_AVAX_CONTRACT_ADDRESS)
    # assert(cf.safekeeper == "0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca")
    print(usdc_avax.balanceOf("0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca"))
    print(tokensToTransfer)

    usdc_avax.approve(
        tokenMessengerCCTP_avax_address, tokensToTransfer, {"from": DEPLOYER}
    )

    # Make a call from an EOA to the Circle contract and get the messageHash
    tokenMessengerCCTP_avax = TokenMessengerMock.at(tokenMessengerCCTP_avax_address)
    tx = tokenMessengerCCTP_avax.depositForBurn(
        tokensToTransfer,
        ETH_DESTINATION_DOMAIN,
        deployedVaultGoerli,
        USDC_AVAX_CONTRACT_ADDRESS,
        {"from": DEPLOYER}
    )

    # Check DepositForBurn event
    assert tx.events["DepositForBurn"]["nonce"] != 0
    assert tx.events["DepositForBurn"]["burnToken"] == USDC_AVAX_CONTRACT_ADDRESS
    assert tx.events["DepositForBurn"]["amount"] == tokensToTransfer
    assert tx.events["DepositForBurn"]["depositor"] == DEPLOYER
    assert tx.events["DepositForBurn"]["mintRecipient"] == deployedVaultGoerli
    assert tx.events["DepositForBurn"]["destinationDomain"] == ETH_DESTINATION_DOMAIN
    assert (
        tx.events["DepositForBurn"]["destinationTokenMessenger"]
        == tokenMessengerCCTP_goerli
    )
    assert tx.events["DepositForBurn"]["destinationCaller"] == "0x0"

    assert tx.events["MessageSent"]["message"] != JUNK_HEX

    message = tx.events["MessageSent"]["message"]
    messageHash = web3.keccak(message)


    print("message: ", message)
    print("messageHash: ", messageHash)

    # We can now fetch the attestation from cirleci. We probably do this in different functions
    # with a real attestation.
    # fetch(`https://iris-api-sandbox.circle.com/attestations/${messageHash}`);
    messageHash = JUNK_HEX


    r = requests.get(f'https://iris-api-sandbox.circle.com/attestations/{messageHash}')
    print(r)
    print(r.text)
    assert False


