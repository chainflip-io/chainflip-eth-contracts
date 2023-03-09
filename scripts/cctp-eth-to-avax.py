import sys
import os

# from . import deploy_contracts

sys.path.append(os.path.abspath("tests"))
from consts import *
from brownie import accounts, Token, TokenMessengerMock, chain, KeyManager, Vault, StakeManager, FLIP
from deploy import deploy_set_Chainflip_contracts, deploy_usdc_contract

import requests


# We probably want to have the same script for AVAX or for ETH, deploying the smart contracts on both.

def main():
    AUTONOMY_SEED = os.environ["SEED"]
    cf_accs = accounts.from_mnemonic(AUTONOMY_SEED, count=10)
    DEPLOYER_ACCOUNT_INDEX = int(os.environ.get("DEPLOYER_ACCOUNT_INDEX") or 0)

    DEPLOYER = cf_accs[DEPLOYER_ACCOUNT_INDEX]
    print(f"DEPLOYER = {DEPLOYER}")

    cf = deploy_set_Chainflip_contracts(
        DEPLOYER, KeyManager, Vault, StakeManager, FLIP, os.environ
    )
    
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
    tokensToTransfer = 1 * 10**6
    assert initialBalance > tokensToTransfer
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

    args = [[usdc_goerli, 0, calldata0], [tokenMessengerCCTP_goerli, 0, calldata1]]
    callDataNoSig = cf.vault.executeActions.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), args
    )
    tx = cf.vault.executeActions(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address), args,
            {"from": DEPLOYER},
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
