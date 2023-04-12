from consts import *
from brownie import network, reverts
from brownie.test import given, strategy
from deploy import deploy_new_stakeManager, deploy_new_vault
from shared_tests import *

# # We want to test that if two instances of the same contract that
# # inherit AggKeyNonceConsumer are whitelisted, the same signature
# # can be used to call any of the two contracts, effectively
# # invalidating the nonce. A frontrunner could use this to grief
# # us and confuse the StateChain.
# @given(
#     st_sender=strategy("address"),
# )
# def test_sig_replay(
#     cf, KeyManager, Vault, StakeManager, FLIP, DeployerStakeManager, st_sender
# ):
#     (_, new_stakeManager) = deploy_new_stakeManager(
#         cf.deployer,
#         KeyManager,
#         StakeManager,
#         FLIP,
#         DeployerStakeManager,
#         cf.keyManager.address,
#         cf.flip.address,
#     )

#     # Trying with stakeManager first and then with Vault. Assuming that we have
#     # removed the whitelist check in the KeyManager.

#     # Manually transfer FLIP funds and upgrade the whitelist to mimic the StateChain.
#     # so we can do the same contract state check.
#     args = [
#         JUNK_HEX,
#         cf.flip.balanceOf(cf.stakeManager.address),
#         new_stakeManager.address,
#         getChainTime() + (2 * CLAIM_DELAY),
#     ]

#     # Generate original calldata for the call that is to be frontrunned
#     callDataNoSig = cf.stakeManager.registerClaim.encode_input(
#         agg_null_sig(cf.keyManager.address, chain.id, cf.stakeManager.address), *args
#     )
#     sigdata = AGG_SIGNER_1.getSigData(
#         callDataNoSig, cf.keyManager.address, cf.stakeManager.address
#     )

#     # Mimic a frontrunning bot - it will now fail because of wrong nonceConsumerAddr. But
#     # if we remove that, then the msgHash should fail.
#     with reverts(REV_MSG_WRONG_NONCECONSUMER):
#         new_stakeManager.registerClaim(
#             sigdata,
#             *args,
#             {"from": st_sender},
#         )

#     # If we try to bypass that, it will still fail msgHash
#     sigdata_modif = sigdata[:]
#     sigdata_modif[6] = new_stakeManager
#     with reverts(REV_MSG_MSGHASH):
#         new_stakeManager.registerClaim(
#             sigdata_modif,
#             *args,
#             {"from": st_sender},
#         )

#     # Try updating the msgHash too to match the updated nonceConsumerAddress.
#     # It should then fail sig verif
#     callDataNoSig_new = cf.stakeManager.registerClaim.encode_input(
#         agg_null_sig(cf.keyManager.address, chain.id, new_stakeManager.address), *args
#     )

#     sigdata_new = AGG_SIGNER_1.getSigData(
#         callDataNoSig_new, cf.keyManager.address, new_stakeManager.address
#     )
#     # But the attacker can't sign, so they have to use the old sigData.sig and
#     # same for the nonceTimesGeneratorAddress
#     sigdata_new[3] = sigdata[3]
#     sigdata_new[5] = sigdata[5]
#     assert sigdata_new[6] == new_stakeManager.address

#     with reverts(REV_MSG_SIG):
#         new_stakeManager.registerClaim(
#             sigdata_new,
#             *args,
#             {"from": st_sender},
#         )

#     # Same trials but by trying to frontrun the call to canConsumeKey
#     # to consume the nonce

#     # Try 0: Calling as is should fail the consumerNonceAddr check
#     with reverts(REV_MSG_WRONG_NONCECONSUMER):
#         cf.keyManager.consumeKeyNonce(sigdata, sigdata[2], {"from": st_sender})

#     # Try 1: Bypassing the consumerNonceAddr check
#     sigdata_modif = sigdata[:]
#     sigdata_modif[6] = st_sender
#     with reverts(REV_MSG_MSGHASH):
#         cf.keyManager.consumeKeyNonce(sigdata_modif, sigdata[2], {"from": st_sender})

#     # Try 2: Also modifying the msgHash so pass both the consumerAddrs check and
#     # the msgHashcheck. Then sig verif should fail.
#     callDataNoSig_new = cf.stakeManager.registerClaim.encode_input(
#         agg_null_sig(cf.keyManager.address, chain.id, st_sender), *args
#     )

#     sigdata_new = AGG_SIGNER_1.getSigData(
#         callDataNoSig_new, cf.keyManager.address, str(st_sender)
#     )
#     # Mimicking crypto.py to get the intermediate hash that we can
#     # "fish" from the call from consumerNonce to KeyManager
#     msgHashHex = cleanHexStr(web3.keccak(hexstr=callDataNoSig_new))

#     # As before, the attacker can't sign, so they have to use the old sigData.sig and
#     # same for the nonceTimesGeneratorAddress
#     sigdata_new[3] = sigdata[3]
#     sigdata_new[5] = sigdata[5]
#     assert sigdata_new[6] == st_sender

#     with reverts(REV_MSG_SIG):
#         cf.keyManager.consumeKeyNonce(
#             sigdata_new, int(msgHashHex, 16), {"from": st_sender}
#         )

#     # Our transaction will pass
#     cf.stakeManager.registerClaim(
#         sigdata,
#         *args,
#         {"from": st_sender},
#     )

#     # Try that in the Vault
#     new_vault = deploy_new_vault(cf.deployer, Vault, KeyManager, cf.keyManager.address)
#     # First fund both vaults with some tokens
#     cf.flip.transfer(cf.vault.address, 1000, {"from": cf.gov})
#     cf.flip.transfer(new_vault.address, 2000, {"from": cf.gov})

#     args = [[cf.flip, cf.BOB, TEST_AMNT]]
#     callDataNoSig = cf.vault.transfer.encode_input(
#         agg_null_sig(cf.keyManager.address, chain.id, cf.vault.address), *args
#     )
#     sigdata = AGG_SIGNER_1.getSigData(
#         callDataNoSig, cf.keyManager.address, cf.vault.address
#     )

#     # Try 0: Calling as is should fail the consumerNonceAddr check
#     with reverts(REV_MSG_WRONG_NONCECONSUMER):
#         new_vault.transfer(sigdata, *args, {"from": st_sender})

#     # Try 1: Bypassing the consumerNonceAddr check
#     sigdata_modif = sigdata[:]
#     sigdata_modif[6] = new_vault.address
#     with reverts(REV_MSG_MSGHASH):
#         new_vault.transfer(sigdata_modif, *args, {"from": st_sender})

#     # Try 2: Also modifying the msgHash so pass both the consumerAddrs check and
#     # the msgHashcheck. Then sig verif should fail.
#     callDataNoSig_new = new_vault.transfer.encode_input(
#         agg_null_sig(cf.keyManager.address, chain.id, new_vault.address), *args
#     )

#     sigdata_new = AGG_SIGNER_1.getSigData(
#         callDataNoSig_new, cf.keyManager.address, new_vault.address
#     )
#     # But the attacker can't sign, so they have to use the old sigData.sig and
#     # same for the nonceTimesGeneratorAddress
#     sigdata_new[3] = sigdata[3]
#     sigdata_new[5] = sigdata[5]
#     assert sigdata_new[6] == new_vault.address

#     with reverts(REV_MSG_SIG):
#         new_vault.transfer(sigdata_new, *args, {"from": st_sender})

#     tx = cf.vault.transfer(sigdata, *args, {"from": st_sender})


@given(
    st_sender=strategy("address"),
    st_new_govKey=strategy("address"),
    st_sig=strategy("uint256", exclude=0),
    st_address=strategy("address"),
)
def test_sig_keyManager_contractMsgHash(
    cf, st_sender, st_new_govKey, st_sig, st_address
):
    # Using setGovKeyWithAggKey to test the replay attack (as a proxy for signed function)

    # Generate original calldata for the call that is to be frontrunned
    contractMsgHash = Signer.generate_contractMsgHash(
        cf.keyManager.setGovKeyWithAggKey, st_new_govKey
    )
    msgHash = Signer.generate_msgHash(
        contractMsgHash, nonces, cf.keyManager.address, cf.keyManager.address
    )
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)

    # For the keyManager anyone can broadcast this transaction

    # Mimic a frontrunning bot - check that changing the arguments will fail
    if st_sender != st_new_govKey:
        with reverts(REV_MSG_SIG):
            cf.keyManager.setGovKeyWithAggKey(
                sigData,
                st_sender,
                {"from": st_sender},
            )

    # Check that changing any of the parameters in sigData won't pass verification
    if st_sig != sigData[0]:
        sigData_modif = sigData[:]
        sigData_modif[0] = st_sig

        with reverts(REV_MSG_SIG):
            cf.keyManager.setGovKeyWithAggKey(
                sigData_modif, st_new_govKey, {"from": st_sender}
            )
    if st_sig != sigData[1]:
        sigData_modif = sigData[:]
        sigData_modif[1] = st_sig
        with reverts(REV_MSG_SIG):
            cf.keyManager.setGovKeyWithAggKey(
                sigData_modif, st_new_govKey, {"from": st_sender}
            )
    if st_address != sigData[2]:
        sigData_modif = sigData[:]
        sigData_modif[2] = st_address
        with reverts(REV_MSG_SIG):
            cf.keyManager.setGovKeyWithAggKey(
                sigData_modif, st_new_govKey, {"from": st_sender}
            )

    # Ensure the original message can be sent
    cf.keyManager.setGovKeyWithAggKey(
        sigData,
        st_new_govKey,
        {"from": st_sender},
    )

    # Check that it can't be replayed as is
    with reverts(REV_MSG_KEYMANAGER_NONCE):
        cf.keyManager.setGovKeyWithAggKey(
            sigData,
            st_new_govKey,
            {"from": st_sender},
        )

    # It can't be replayed increasing the nonce
    sigData_modif = sigData[:]
    sigData_modif[1] += 1
    with reverts(REV_MSG_SIG):
        cf.keyManager.setGovKeyWithAggKey(
            sigData_modif,
            st_new_govKey,
            {"from": st_sender},
        )

    # Reusing the call to call consumeKeyNonce will fail as there is the nonceConsumerAddr(msg.sender)
    # hashed into consumeKeyNonce
    with reverts(REV_MSG_SIG):
        cf.keyManager.consumeKeyNonce(
            sigData,
            contractMsgHash,
            {"from": st_sender},
        )


@given(
    st_sender=strategy("address"),
    st_new_govKey=strategy("address"),
    st_address=strategy("address"),
    st_chainId=strategy("uint256"),
)
def test_sig_keyManager_msgHash(cf, st_sender, st_new_govKey, st_address, st_chainId):

    # Sign over another KeyManagerAddress and check that it doesn't pass
    with reverts(REV_MSG_SIG):
        signed_call_cf(
            cf,
            cf.keyManager.address,
            cf.keyManager.setGovKeyWithAggKey,
            st_new_govKey,
            sender=st_sender,
            keyManager=st_address,
        )

    # Sign over another nonceConsumerAddr and check that it doesn't pass
    with reverts(REV_MSG_SIG):
        signed_call_cf(
            cf,
            st_address,
            cf.keyManager.setGovKeyWithAggKey,
            st_new_govKey,
            sender=st_sender,
        )

    # Sign over another ChainID and check that it doesn't pass
    if st_chainId == chain.id:
        return
    contractMsgHash = Signer.generate_contractMsgHash(
        cf.keyManager.setGovKeyWithAggKey, st_new_govKey
    )
    msgHash = Signer.generate_msgHash(
        contractMsgHash,
        nonces,
        cf.keyManager.address,
        cf.keyManager.address,
        chainId=st_chainId,
    )
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)
    with reverts(REV_MSG_SIG):
        cf.keyManager.setGovKeyWithAggKey(
            sigData,
            st_new_govKey,
            {"from": st_sender},
        )


@given(
    st_sig=strategy("uint256", exclude=0),
)
def test_sig_keyManager_bruteforce(cf, st_sig):
    contractMsgHash = Signer.generate_contractMsgHash(
        cf.keyManager.setGovKeyWithAggKey, cf.SAFEKEEPER
    )
    msgHash = Signer.generate_msgHash(
        contractMsgHash, nonces, cf.keyManager.address, cf.keyManager.address
    )
    sigData = AGG_SIGNER_1.generate_sigData(msgHash, nonces)
    if sigData[0] != st_sig:
        sigData[0] = st_sig
        with reverts(REV_MSG_SIG):
            cf.keyManager.setGovKeyWithAggKey(
                sigData,
                cf.SAFEKEEPER,
                {"from": cf.SAFEKEEPER},
            )


# TODO: Do the same tests for another contract (either StakeManager or Vault). That should also test the
# consumerNonceAddress, which we are also testing here but in the keymanagr it's the same.
# Especially in those contracts it's important to test the replay attack as the contractMsgHash will be
# hashed with the same parameters as we can call externally via consumeKeyNonce.
