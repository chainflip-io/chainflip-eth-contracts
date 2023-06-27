from consts import *
from brownie import reverts
from brownie.test import given, strategy
from deploy import deploy_new_stateChainGateway, deploy_new_vault, deploy_new_keyManager
from shared_tests import *

# Using a function for each contract to test the replay attack as a proxy for signed function.
# No need to test every single function, since when signed_call_cf is working, if any function
# is not properly implemented at the solidity level, it will fail on the regular tests. Any
# missing parameters when hashing will yield a different hash and signature.


@given(
    st_sender=strategy("address"),
    st_new_govKey=strategy("address"),
    st_sig=strategy("uint256", exclude=0),
    st_address=strategy("address"),
)
def test_sig_keyManager(cf, st_sender, st_new_govKey, st_sig, st_address, KeyManager):
    # Generate original calldata for the call that is to be frontrunned
    contractMsgHash = Signer.generate_contractMsgHash(
        cf.keyManager.setGovKeyWithAggKey, st_new_govKey
    )
    msgHash = Signer.generate_msgHash(
        contractMsgHash, nonces, cf.keyManager.address, cf.keyManager.address
    )
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)

    # Check that changing the arguments will fail
    if st_sender != st_new_govKey:
        with reverts(REV_MSG_SIG):
            cf.keyManager.setGovKeyWithAggKey(
                sigData,
                st_sender,
                {"from": st_sender},
            )

    # Check that we can't use the signature for another function in the same
    # contract that has the same arguments (different function selector)
    with reverts(REV_MSG_SIG):
        cf.keyManager.setCommKeyWithAggKey(
            sigData,
            st_new_govKey,
            {"from": st_sender},
        )

    contractMsgHash_sigVerification(
        cf.keyManager.setGovKeyWithAggKey,
        cf.keyManager,
        contractMsgHash,
        sigData,
        st_sig,
        st_sender,
        st_address,
        st_new_govKey,
    )

    newKeyManager_replay_test(
        cf,
        KeyManager,
        None,
        None,
        sigData,
        contractMsgHash,
        st_sender,
        st_new_govKey,
    )


# We want to test that if there are two instances of the same contract that
# inherit AggKeyNonceConsumer, the same signature cannot be used to call any
# of the two contracts.
@given(
    st_sender=strategy("address"),
    st_sig=strategy("uint256", exclude=0),
    st_address=strategy("address"),
    st_amount=strategy("uint256", exclude=0),
)
def test_sig_stateChainGateway(
    cf,
    KeyManager,
    StateChainGateway,
    FLIP,
    DeployerStateChainGateway,
    st_sender,
    st_sig,
    st_address,
    st_amount,
):
    (_, new_stateChainGateway) = deploy_new_stateChainGateway(
        cf.deployer,
        KeyManager,
        StateChainGateway,
        FLIP,
        DeployerStateChainGateway,
        cf.keyManager.address,
        cf.flip.address,
        MIN_FUNDING,
        REDEMPTION_DELAY,
    )

    args = [
        JUNK_HEX,
        cf.flip.balanceOf(cf.stateChainGateway.address),
        cf.stateChainGateway.address,
        getChainTime() + (2 * REDEMPTION_DELAY),
    ]

    # Generate original calldata for the call that is to be frontrunned
    contractMsgHash = Signer.generate_contractMsgHash(
        cf.stateChainGateway.registerRedemption, *args
    )
    msgHash = Signer.generate_msgHash(
        contractMsgHash, nonces, cf.keyManager.address, cf.stateChainGateway.address
    )
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)

    # Check that changing the arguments will fail
    args_modif = args[:]
    args_modif[1] = st_amount
    with reverts(REV_MSG_SIG):
        cf.stateChainGateway.registerRedemption(
            sigData,
            *args_modif,
            {"from": st_sender},
        )

    # Mimic a frontrunning bot making the same call to the new stateChainGateway. It should
    # fail due to the nonceConsumer being different (msg.sender is hashed over)
    with reverts(REV_MSG_SIG):
        new_stateChainGateway.registerRedemption(
            sigData,
            *args,
            {"from": st_sender},
        )

    contractMsgHash_sigVerification(
        cf.stateChainGateway.registerRedemption,
        cf.keyManager,
        contractMsgHash,
        sigData,
        st_sig,
        st_sender,
        st_address,
        *args,
    )

    newKeyManager_replay_test(
        cf,
        KeyManager,
        cf.stateChainGateway,
        cf.stateChainGateway.registerRedemption,
        sigData,
        contractMsgHash,
        st_sender,
        *args,
    )


@given(
    st_sender=strategy("address"),
    st_sig=strategy("uint256", exclude=0),
    st_address=strategy("address"),
    st_amount=strategy("uint256", exclude=0),
)
def test_sig_vault(cf, KeyManager, Vault, st_sender, st_sig, st_address, st_amount):

    new_vault = deploy_new_vault(cf.deployer, Vault, KeyManager, cf.keyManager.address)

    # First fund both vaults with some tokens
    cf.flip.transfer(cf.vault.address, 1000, {"from": cf.gov})
    cf.flip.transfer(new_vault.address, 2000, {"from": cf.gov})

    args = [[cf.flip, cf.BOB, TEST_AMNT]]

    contractMsgHash = Signer.generate_contractMsgHash(cf.vault.transfer, *args)
    msgHash = Signer.generate_msgHash(
        contractMsgHash, nonces, cf.keyManager.address, cf.vault.address
    )
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)

    # Check that changing the arguments will fail
    args_modif = args[0][:]
    args_modif[2] = st_amount
    with reverts(REV_MSG_SIG):
        cf.vault.transfer(
            sigData,
            [*args_modif],
            {"from": st_sender},
        )

    # Mimic a frontrunning bot making the same call to the new vault. It should
    # fail due to the nonceConsumer being different (msg.sender is hashed over)
    with reverts(REV_MSG_SIG):
        new_vault.transfer(sigData, *args, {"from": st_sender})

    contractMsgHash_sigVerification(
        cf.vault.transfer,
        cf.keyManager,
        contractMsgHash,
        sigData,
        st_sig,
        st_sender,
        st_address,
        *args,
    )

    newKeyManager_replay_test(
        cf,
        KeyManager,
        cf.vault,
        cf.vault.transfer,
        sigData,
        contractMsgHash,
        st_sender,
        *args,
    )


@given(
    st_sender=strategy("address"),
    st_new_govKey=strategy("address"),
    st_address=strategy("address"),
    st_chainId=strategy("uint256"),
    st_amount=strategy("uint256", exclude=0),
)
def test_sig_msgHash(cf, st_sender, st_new_govKey, st_address, st_chainId, st_amount):

    msgHash_verification(
        cf,
        cf.keyManager.setGovKeyWithAggKey,
        st_sender,
        st_address,
        st_chainId,
        st_new_govKey,
    )

    args = [
        JUNK_HEX,
        st_amount,
        st_address,
        getChainTime(),
    ]
    msgHash_verification(
        cf,
        cf.stateChainGateway.registerRedemption,
        st_sender,
        st_address,
        st_chainId,
        *args,
    )

    args = [[st_address, st_address]]
    msgHash_verification(
        cf,
        cf.vault.fetchBatch,
        st_sender,
        st_address,
        st_chainId,
        args,
    )


def contractMsgHash_sigVerification(
    fcn, keyManager, contractMsgHash, sigData, st_sig, st_sender, st_address, *args
):
    # Try bruteforcing
    st_sigData = [st_sig, sigData[1], st_address]
    with reverts(REV_MSG_SIG):
        fcn(
            st_sigData,
            *args,
            {"from": st_sender},
        )

    # Check that changing any of the parameters in sigData won't pass verification
    # This could technically revert, as it could be bruteforce, especially if
    # the hypothesis generation is.scgart. But it shouldn't happen in practice.

    # Bruteforce the signature
    sigData_modif = sigData[:]
    sigData_modif[0] = st_sig
    with reverts(REV_MSG_SIG):
        fcn(sigData_modif, *args, {"from": st_sender})

    # Bruteforce the kTimesGAddress
    sigData_modif = sigData[:]
    sigData_modif[2] = st_address
    with reverts(REV_MSG_SIG):
        fcn(sigData_modif, *args, {"from": st_sender})

    # Check that changing the nonce will fail. Seems like the hypothesis is.scgart
    # enough to figure this one out, so we add a check.
    if st_sig != sigData_modif[1]:
        sigData_modif = sigData[:]
        sigData_modif[1] = st_sig
        with reverts(REV_MSG_SIG):
            fcn(sigData_modif, *args, {"from": st_sender})

    # Check we can't bruteforce the signature by changing both sig and kTimesGAddress
    sigData_modif = sigData[:]
    sigData_modif[0] = st_sig
    sigData_modif[2] = st_address
    with reverts(REV_MSG_SIG):
        fcn(sigData_modif, *args, {"from": st_sender})

    # Ensure the original message can be sent
    fcn(
        sigData,
        *args,
        {"from": st_sender},
    )

    # Check that it can't be replayed as is
    with reverts(REV_MSG_KEYMANAGER_NONCE):
        fcn(
            sigData,
            *args,
            {"from": st_sender},
        )

    # It can't be replayed increasing the nonce
    sigData_modif = sigData[:]
    sigData_modif[1] += 1
    with reverts(REV_MSG_SIG):
        fcn(
            sigData_modif,
            *args,
            {"from": st_sender},
        )

    # Reusing the call to call consumeKeyNonce will fail as there is the nonceConsumerAddr(msg.sender)
    # hashed into consumeKeyNonce
    with reverts(REV_MSG_SIG):
        keyManager.consumeKeyNonce(
            sigData,
            contractMsgHash,
            {"from": st_sender},
        )


def msgHash_verification(cf, fcn, st_sender, st_address, st_chainId, *args):
    nonceConsumerAddress = fcn._address

    # Sign over another KeyManagerAddress and check that it doesn't pass
    with reverts(REV_MSG_SIG):
        signed_call_cf(
            cf,
            fcn,
            *args,
            sender=st_sender,
            keyManager=st_address,
        )

    # Sign over another nonceConsumerAddr and check that it doesn't pass
    contractMsgHash = Signer.generate_contractMsgHash(fcn, *args)
    msgHash = Signer.generate_msgHash(
        contractMsgHash,
        nonces,
        cf.keyManager.address,
        st_address,
    )
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)
    with reverts(REV_MSG_SIG):
        fcn(
            sigData,
            *args,
            {"from": st_sender},
        )

    # Sign over another ChainID and check that it doesn't pass
    if st_chainId == chain.id:
        return

    contractMsgHash = Signer.generate_contractMsgHash(fcn, *args)
    msgHash = Signer.generate_msgHash(
        contractMsgHash,
        nonces,
        cf.keyManager.address,
        nonceConsumerAddress,
        chainId=st_chainId,
    )
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)
    with reverts(REV_MSG_SIG):
        fcn(
            sigData,
            *args,
            {"from": st_sender},
        )


def newKeyManager_replay_test(
    cf, KeyManager, nonceConsumer, fcn, sigData, contractMsgHash, st_sender, *args
):
    # Deploy a new KeyManager
    new_keyManager = deploy_new_keyManager(
        cf.deployer,
        KeyManager,
        cf.keyManager.getAggregateKey(),
        cf.keyManager.getGovernanceKey(),
        cf.keyManager.getCommunityKey(),
    )

    # Try to consume the nonce via consumeKeyNonce replaying a signature to the previous KeyManager
    with reverts(REV_MSG_SIG):
        new_keyManager.consumeKeyNonce(
            sigData,
            contractMsgHash,
            {"from": st_sender},
        )

    # Pointing the contract to the new keyManager and try to replay the call.
    # For nonceConsumer contracts, we need to point at the new keyManager
    if nonceConsumer != None:
        signed_call_cf(
            cf,
            nonceConsumer.updateKeyManager,
            new_keyManager.address,
            False,
            sender=st_sender,
        )
    else:
        # Hardcoding the function here due to brownie having limitations concatenating functions
        fcn = new_keyManager.setGovKeyWithAggKey

    # Try to consume the nonce with a call replaying a signature to the previous KeyManager
    with reverts(REV_MSG_SIG):
        fcn(
            sigData,
            *args,
            {"from": st_sender},
        )
