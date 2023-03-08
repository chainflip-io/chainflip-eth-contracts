from consts import *
from brownie import reverts
from utils import *
from shared_tests import *


# Only run this tests with a separate terminal running a Goerli fork
# npx hardhat node --fork https://goerli.infura.io/v3/<INFURA_API>

#  Running it automatically will fail, as this accounts are specific to Forked Goerli
def test_depositForBurn(cf, Token, TokenMessengerMock):
    # Check we are in a Goerli fork
    # print(web3.eth.get_balance("0xc6e2459991BfE27cca6d86722F35da23A1E4Cb97"))
    # print(web3.eth.get_balance("0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca"))

    ## Fund the Vault with our initial USDC
    user_address = "0x37876B47DEE43492DAC3d87F7682df52dDBC65Ca"
    usdc_goerli = Token.at("0x07865c6e87b9f70255377e024ace6630c1eaa37f")

    # We have a balance of 10*10**6
    # We force the transaction to be sent by the user but in reality we would
    # need to intput the SEED and sign it from there.
    initialBalance = usdc_goerli.balanceOf(user_address)
    assert initialBalance == 10 * 10**6
    usdc_goerli.transfer(cf.vault.address, initialBalance, {"from": user_address})

    assert usdc_goerli.balanceOf(cf.vault.address) == initialBalance
    assert usdc_goerli.balanceOf(user_address) == 0

    # Craft a transaction to the CCTP address. For now using this instead of Brownie
    # encode_input because I want to avoid needing the contract here.
    tokenMessengerCCTP_goerli = TokenMessengerMock.at(
        "0xd0c3da58f55358142b8d3e06c1c30c5c6114efe8"
    )
    tokenMessengerCCTP_avax_address = "0xeb08f243e5d3fcff26a9e38ae5520a669f4019d0"

    calldata0 = usdc_goerli.approve.encode_input(
        tokenMessengerCCTP_goerli.address, initialBalance
    )
    AVAX_DESTINATION_DOMAIN = 1
    destinationAddressInBytes32 = JUNK_HEX
    USDC_ETH_CONTRACT_ADDRESS = usdc_goerli
    calldata1 = tokenMessengerCCTP_goerli.depositForBurn.encode_input(
        initialBalance,
        AVAX_DESTINATION_DOMAIN,
        destinationAddressInBytes32,
        USDC_ETH_CONTRACT_ADDRESS,
    )

    tx = signed_call_cf(
        cf,
        cf.vault.executeActions,
        [[usdc_goerli, 0, calldata0], [tokenMessengerCCTP_goerli, 0, calldata1]],
    )

    assert usdc_goerli.balanceOf(cf.vault.address) == 0

    print("Interacting address: ", tokenMessengerCCTP_goerli)

    # Check DepositForBurn event
    assert tx.events["DepositForBurn"]["nonce"] != 0
    assert tx.events["DepositForBurn"]["burnToken"] == usdc_goerli
    assert tx.events["DepositForBurn"]["amount"] == initialBalance
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
