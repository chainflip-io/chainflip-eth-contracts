from consts import *
from brownie import network, reverts
from brownie.test import given, strategy
from deploy import deploy_new_stakeManager, deploy_new_vault


# We want to test that if two instances of the same contract that
# inherit AggKeyNonceConsumer are whitelisted, the same signature
# can be used to call any of the two contracts, effectively
# invalidating the nonce. A frontrunner could use this to grief
# us and confuse the StateChain.
@given(
    st_sender=strategy("address"),
)
def test_sig_replay(
    cf, KeyManager, Vault, StakeManager, FLIP, DeployerStakeManager, st_sender
):
    (_, new_stakeManager) = deploy_new_stakeManager(
        cf.deployer,
        KeyManager,
        StakeManager,
        FLIP,
        DeployerStakeManager,
        cf.keyManager.address,
        cf.flip.address,
    )

    # Trying with stakeManager first and then with Vault. Assuming that we have
    # removed the whitelist check in the KeyManager.
    rev_msg_nonceConsumerAddr = "KeyManager: wrong nonceConsumerAddr"
    # Manually transfer FLIP funds and upgrade the whitelist to mimic the StateChain.
    # so we can do the same contract state check.
    args = [
        JUNK_HEX,
        cf.flip.balanceOf(cf.stakeManager.address),
        new_stakeManager.address,
        getChainTime() + (2 * CLAIM_DELAY),
    ]

    # Generate original calldata for the call that is to be frontrunned
    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id, cf.stakeManager.address), *args
    )
    sigdata = AGG_SIGNER_1.getSigData(
        callDataNoSig, cf.keyManager.address, cf.stakeManager.address
    )

    # Mimic a frontrunning bot - it will now fail because of wrong nonceConsumerAddr. But
    # if we remove that, then the msgHash should fail.
    with reverts(rev_msg_nonceConsumerAddr):
        new_stakeManager.registerClaim(
            sigdata,
            *args,
            {"from": st_sender},
        )

    # If we try to bypass that, it will still fail msgHash
    sigdata_modif = sigdata[:]
    sigdata_modif[6] = new_stakeManager
    with reverts(REV_MSG_MSGHASH):
        new_stakeManager.registerClaim(
            sigdata_modif,
            *args,
            {"from": st_sender},
        )

    # Try updating the msgHash too to match the updated nonceConsumerAddress.
    # It should then fail sig verif
    callDataNoSig_new = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id, new_stakeManager.address), *args
    )

    sigdata_new = AGG_SIGNER_1.getSigData(
        callDataNoSig_new, cf.keyManager.address, new_stakeManager.address
    )
    # But the attacker can't sign, so they have to use the old sigData.sig and
    # same for the nonceTimesGeneratorAddress
    sigdata_new[3] = sigdata[3]
    sigdata_new[5] = sigdata[5]
    assert sigdata_new[6] == new_stakeManager.address

    with reverts(REV_MSG_SIG):
        new_stakeManager.registerClaim(
            sigdata_new,
            *args,
            {"from": st_sender},
        )

    # Same trials but by trying to frontrun the call to canConsumeKey
    # to consume the nonce

    # Try 0: Calling as is should fail the consumerNonceAddr check
    with reverts(rev_msg_nonceConsumerAddr):
        cf.keyManager.consumeKeyNonce(sigdata, sigdata[2], {"from": st_sender})

    # Try 1: Bypassing the consumerNonceAddr check
    sigdata_modif = sigdata[:]
    sigdata_modif[6] = st_sender
    with reverts(REV_MSG_MSGHASH):
        cf.keyManager.consumeKeyNonce(sigdata_modif, sigdata[2], {"from": st_sender})

    # Try 2: Also modifying the msgHash so pass both the consumerAddrs check and
    # the msgHashcheck. Then sig verif should fail.
    callDataNoSig_new = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id, st_sender), *args
    )

    sigdata_new = AGG_SIGNER_1.getSigData(
        callDataNoSig_new, cf.keyManager.address, str(st_sender)
    )
    # Mimicking crypto.py to get the intermediate hash that we can
    # "fish" from the call from consumerNonce to KeyManager
    msgHashHex = cleanHexStr(web3.keccak(hexstr=callDataNoSig_new))

    # As before, the attacker can't sign, so they have to use the old sigData.sig and
    # same for the nonceTimesGeneratorAddress
    sigdata_new[3] = sigdata[3]
    sigdata_new[5] = sigdata[5]
    assert sigdata_new[6] == st_sender

    with reverts(REV_MSG_SIG):
        cf.keyManager.consumeKeyNonce(
            sigdata_new, int(msgHashHex, 16), {"from": st_sender}
        )

    # Our transaction will pass
    cf.stakeManager.registerClaim(
        sigdata,
        *args,
        {"from": st_sender},
    )

    # # Try that in the Vault
    # new_vault = deploy_new_vault(cf.deployer, Vault, KeyManager, cf.keyManager.address)
    # # First fund both vaults with some tokens
    # cf.flip.transfer(cf.vault.address, 1000, {"from": cf.gov})
    # cf.flip.transfer(new_vault.address, 2000, {"from": cf.gov})

    # # Update whitelist to include both Vaults and dewhitelist new_stakeManager (just for housekeeping)
    # current_whitelist = [
    #     cf.vault.address,
    #     cf.flip.address,
    #     new_stakeManager.address,
    #     cf.stakeManager.address,
    # ]
    # new_whitelist = [
    #     cf.vault.address,
    #     cf.flip.address,
    #     new_stakeManager.address,
    #     new_vault.address,
    # ]
    # args = [current_whitelist, new_whitelist]
    # callDataNoSig = cf.keyManager.updateCanConsumeKeyNonce.encode_input(
    #     agg_null_sig(cf.keyManager.address, chain.id, cf.keyManager.address), *args
    # )
    # cf.keyManager.updateCanConsumeKeyNonce(
    #     AGG_SIGNER_1.getSigDataWithNonces(
    #         callDataNoSig, nonces, cf.keyManager.address, cf.keyManager.address
    #     ),
    #     *args,
    #     {"from": st_sender},
    # )

    # args = [[cf.flip, cf.BOB, TEST_AMNT]]
    # callDataNoSig = cf.vault.transfer.encode_input(
    #     agg_null_sig(cf.keyManager.address, chain.id, cf.vault.address), *args
    # )
    # sigdata = AGG_SIGNER_1.getSigData(
    #     callDataNoSig, cf.keyManager.address, cf.vault.address
    # )

    # # Bot frontruns us calling the new contract
    # with reverts(REV_MSG_MSGHASH):
    #     new_vault.transfer(sigdata, *args, {"from": st_sender})

    # tx = cf.vault.transfer(sigdata, *args, {"from": st_sender})


# TODO: Same as for Vault and StakeManager will need to be tried for
# a signed function in the KeyManager (e.g. setGovKeyWithAggKey)
