from brownie import reverts, web3
from brownie.test import given, strategy
from consts import *
from shared_tests import *


@given(
    st_amounts=strategy(
        "uint[]", max_value=TEST_AMNT, max_length=int(INIT_TOKEN_SUPPLY / TEST_AMNT)
    ),
    st_swapIDs=strategy("bytes32[]", unique=True),
    st_tokenBools=strategy("bool[]"),
)
def test_deployAndFetchBatch(cf, token, Deposit, st_amounts, st_swapIDs, st_tokenBools):
    trimToShortest([st_amounts, st_swapIDs, st_tokenBools])
    tokens = [token if b == True else NATIVE_ADDR for b in st_tokenBools]
    tokenTotal = 0
    nativeTotal = 0

    for am, id, tok in zip(st_amounts, st_swapIDs, tokens):
        # Get the address to deposit to and deposit
        if tok == token:
            depositAddr = getCreate2Addr(
                cf.vault.address, id.hex(), Deposit, cleanHexStrPad(tok.address)
            )
            tok.transfer(depositAddr, am, {"from": cf.SAFEKEEPER})
            tokenTotal += am
        else:
            depositAddr = getCreate2Addr(
                cf.vault.address, id.hex(), Deposit, cleanHexStrPad(tok)
            )
            cf.SAFEKEEPER.transfer(depositAddr, am)
            nativeTotal += am

    assert token.balanceOf(cf.vault) == 0
    assert web3.eth.get_balance(cf.vault.address) == 0

    # Fetch the deposit
    deployFetchParams = [craftDeployFetchParamsArray(st_swapIDs, tokens)]

    signed_call_cf(cf, cf.vault.deployAndFetchBatch, *deployFetchParams)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert token.balanceOf(cf.vault.address) == tokenTotal
    assert web3.eth.get_balance(cf.vault.address) == nativeTotal


def test_deployAndFetchBatch_rev_sig(cf, token):
    for tok in [token, NATIVE_ADDR]:
        args = [[JUNK_HEX_PAD, tok]]

        sigData = AGG_SIGNER_1.getSigDataWithNonces(
            cf.keyManager, cf.vault.deployAndFetchBatch, nonces, args
        )

        sigData_modif = sigData[:]
        sigData_modif[0] += 1

        with reverts(REV_MSG_SIG):
            cf.vault.deployAndFetchBatch(sigData_modif, args, {"from": cf.ALICE})

        sigData_modif = sigData[:]
        sigData_modif[1] += 1

        with reverts(REV_MSG_SIG):
            cf.vault.deployAndFetchBatch(sigData_modif, args, {"from": cf.ALICE})

        sigData_modif = sigData[:]
        sigData_modif[2] = NON_ZERO_ADDR

        with reverts(REV_MSG_SIG):
            cf.vault.deployAndFetchBatch(sigData_modif, args, {"from": cf.ALICE})


# Deploying a Deposit on an address that already contains a Deposit should revert.
def test_deployAndFetchBatch_rev_deployed(cf, token):
    for tok in [token, NATIVE_ADDR]:
        signed_call_cf(cf, cf.vault.deployAndFetchBatch, [[JUNK_HEX_PAD, tok]])
        with reverts():
            signed_call_cf(cf, cf.vault.deployAndFetchBatch, [[JUNK_HEX_PAD, tok]])


# This is a test to catch when the Deposit bytecode changes
def test_getCreate2Addr(Deposit):
    vault_address = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"
    flip_address = "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9"

    depositAddr = getCreate2Addr(
        vault_address,
        cleanHexStrPad(web3.toHex(420696969)),
        Deposit,
        cleanHexStrPad(NATIVE_ADDR),
    )

    assert depositAddr == "0x457f6b184D6Ec61cC25e352E0AC67796736D0331"

    depositAddr = getCreate2Addr(
        vault_address, JUNK_HEX_PAD, Deposit, cleanHexStrPad(flip_address)
    )

    assert depositAddr == "0x23b3024c5c2F6D40dB9829C7Ea194fa7855C4ca6"
