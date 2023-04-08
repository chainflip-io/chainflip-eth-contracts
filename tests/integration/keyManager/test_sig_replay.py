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

    # We try this with the StakeManager, as it's the most problematic case
    new_whitelist = [
        cf.flip.address,
        cf.vault.address,
        cf.stakeManager.address,
        new_stakeManager.address,
    ]

    args = [cf.whitelisted, new_whitelist]
    callDataNoSig = cf.keyManager.updateCanConsumeKeyNonce.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id, cf.keyManager.address), *args
    )
    cf.keyManager.updateCanConsumeKeyNonce(
        AGG_SIGNER_1.getSigDataWithNonces(
            callDataNoSig, nonces, cf.keyManager.address, cf.keyManager.address
        ),
        *args,
        {"from": st_sender},
    )

    # Manually transfer FLIP funds and upgrade the whitelist to mimic the StateChain.
    # so we can do the same contract state check.
    args = [
        JUNK_HEX,
        cf.flip.balanceOf(cf.stakeManager.address),
        new_stakeManager.address,
        getChainTime() + (2 * CLAIM_DELAY),
    ]

    callDataNoSig = cf.stakeManager.registerClaim.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id, cf.stakeManager.address), *args
    )

    sigdata = AGG_SIGNER_1.getSigData(
        callDataNoSig, cf.keyManager.address, cf.stakeManager.address
    )

    # Mimic a frontrunning bot - it will now fail because of wrong nonceConsumerAddr
    with reverts("KeyManager: wrong nonceConsumerAddr"):
        new_stakeManager.registerClaim(
            sigdata,
            *args,
            {"from": st_sender},
        )

    # Check if a frontrunning bot could consume our nonce if we have "removed" the whitelist.
    # First it will fail due towhitelist.
    msgHashHex = cleanHexStr(web3.keccak(hexstr=callDataNoSig))
    with reverts(REV_MSG_WHITELIST):
        cf.keyManager.consumeKeyNonce(sigdata, msgHashHex, {"from": st_sender})

    # Mimic removal of whitelist
    st_sender_whitelisted = new_whitelist[:]
    st_sender_whitelisted.append(st_sender)

    args_aux = [new_whitelist, st_sender_whitelisted]
    callDataNoSig = cf.keyManager.updateCanConsumeKeyNonce.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id, cf.keyManager.address), *args_aux
    )
    cf.keyManager.updateCanConsumeKeyNonce(
        AGG_SIGNER_1.getSigDataWithNonces(
            callDataNoSig, nonces, cf.keyManager.address, cf.keyManager.address
        ),
        *args_aux,
        {"from": st_sender},
    )

    # Attacker consumes our nonce without needing to resign. They do need to modify
    # the consumerKeyNonce but that's not a problem. They don't even need to rehash
    # the message, as we are using the same sigData.sig and same msgHashHex.
    sigdata_modif = sigdata[:]
    sigdata_modif[6] = st_sender
    cf.keyManager.consumeKeyNonce(sigdata_modif, msgHashHex, {"from": st_sender})

    # Our transaction fails due to nonce being consumed.
    cf.stakeManager.registerClaim(
        sigdata,
        *args,
        {"from": st_sender},
    )

    # Try that in the Vault
    new_vault = deploy_new_vault(cf.deployer, Vault, KeyManager, cf.keyManager.address)
    # First fund both vaults with some tokens
    cf.flip.transfer(cf.vault.address, 1000, {"from": cf.gov})
    cf.flip.transfer(new_vault.address, 2000, {"from": cf.gov})

    # Update whitelist to include both Vaults and dewhitelist new_stakeManager (just for housekeeping)
    current_whitelist = [
        cf.vault.address,
        cf.flip.address,
        new_stakeManager.address,
        cf.stakeManager.address,
    ]
    new_whitelist = [
        cf.vault.address,
        cf.flip.address,
        new_stakeManager.address,
        new_vault.address,
    ]
    args = [current_whitelist, new_whitelist]
    callDataNoSig = cf.keyManager.updateCanConsumeKeyNonce.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id, cf.keyManager.address), *args
    )
    cf.keyManager.updateCanConsumeKeyNonce(
        AGG_SIGNER_1.getSigDataWithNonces(
            callDataNoSig, nonces, cf.keyManager.address, cf.keyManager.address
        ),
        *args,
        {"from": st_sender},
    )

    args = [[cf.flip, cf.BOB, TEST_AMNT]]
    callDataNoSig = cf.vault.transfer.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id, cf.vault.address), *args
    )
    sigdata = AGG_SIGNER_1.getSigData(
        callDataNoSig, cf.keyManager.address, cf.vault.address
    )

    # Bot frontruns us calling the new contract
    with reverts(REV_MSG_MSGHASH):
        new_vault.transfer(sigdata, *args, {"from": st_sender})

    tx = cf.vault.transfer(sigdata, *args, {"from": st_sender})
