from consts import *
from brownie import reverts, chain, web3
from utils import *

# ----------Vault----------


def fetchDepositEth(cf, vault, DepositEth, **kwargs):
    amount = kwargs.get("amount", TEST_AMNT)

    # Get the address to deposit to and deposit
    depositAddr = getCreate2Addr(vault.address, JUNK_HEX_PAD, DepositEth, "")

    assert cf.DEPLOYER.balance() >= amount
    cf.DEPLOYER.transfer(depositAddr, amount)

    balanceVaultBefore = vault.balance()

    # Fetch the deposit
    signed_call_cf(cf, vault.fetchDepositEth, JUNK_HEX_PAD, sender=cf.ALICE)

    assert web3.eth.get_balance(web3.toChecksumAddress(depositAddr)) == 0
    assert vault.balance() == balanceVaultBefore + amount

    return depositAddr


# Test transfer function from a vault with funds
def transfer_eth(cf, vault, receiver, amount):
    startBalVault = vault.balance()
    assert startBalVault >= amount
    startBalRecipient = receiver.balance()

    tx = signed_call_cf(cf, vault.transfer, [ETH_ADDR, receiver, amount])

    assert vault.balance() - startBalVault == -amount

    # Take into account gas transfer if receiver is the address sending the transfer call (a[0]==cf.DEPLOYER)
    gasSpent = calculateGasTransaction(tx) if receiver == cf.DEPLOYER else 0
    assert receiver.balance() - startBalRecipient == amount - gasSpent


# ----------KeyManager----------

# Set keys


def setAggKeyWithAggKey_test(cf):
    checkCurrentKeys(cf, AGG_SIGNER_1.getPubDataWith0x(), cf.GOVERNOR, cf.COMMUNITY_KEY)

    tx = signed_call_cf(
        cf,
        cf.keyManager.setAggKeyWithAggKey,
        AGG_SIGNER_2.getPubData(),
        sender=cf.ALICE,
    )
    checkCurrentKeys(cf, AGG_SIGNER_2.getPubDataWith0x(), cf.GOVERNOR, cf.COMMUNITY_KEY)

    assert tx.events["AggKeySetByAggKey"][0].values() == [
        AGG_SIGNER_1.getPubDataWith0x(),
        AGG_SIGNER_2.getPubDataWith0x(),
    ]


def setKey_rev_newPubKeyX_test(cf):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()

    with reverts(REV_MSG_PUB_KEY_X):
        signed_call_cf(
            cf,
            cf.keyManager.setAggKeyWithAggKey,
            BAD_AGG_KEY,
            sender=cf.ALICE,
        )


def setAggKeyWithGovKey_test(cf):
    checkCurrentKeys(cf, AGG_SIGNER_1.getPubDataWith0x(), cf.GOVERNOR, cf.COMMUNITY_KEY)

    tx = cf.keyManager.setAggKeyWithGovKey(
        AGG_SIGNER_2.getPubData(), {"from": cf.GOVERNOR}
    )

    checkCurrentKeys(cf, AGG_SIGNER_2.getPubDataWith0x(), cf.GOVERNOR, cf.COMMUNITY_KEY)

    assert tx.events["AggKeySetByGovKey"][0].values() == [
        AGG_SIGNER_1.getPubDataWith0x(),
        AGG_SIGNER_2.getPubDataWith0x(),
    ]


def setGovKeyWithGovKey_test(cf):
    checkCurrentKeys(cf, AGG_SIGNER_1.getPubDataWith0x(), cf.GOVERNOR, cf.COMMUNITY_KEY)

    tx = cf.keyManager.setGovKeyWithGovKey(cf.GOVERNOR_2, {"from": cf.GOVERNOR})

    checkCurrentKeys(
        cf, AGG_SIGNER_1.getPubDataWith0x(), cf.GOVERNOR_2, cf.COMMUNITY_KEY
    )

    assert tx.events["GovKeySetByGovKey"][0].values() == [cf.GOVERNOR, cf.GOVERNOR_2]


def setGovKeyWithAggKey_test(cf):
    checkCurrentKeys(cf, AGG_SIGNER_1.getPubDataWith0x(), cf.GOVERNOR, cf.COMMUNITY_KEY)

    tx = signed_call_cf(
        cf,
        cf.keyManager.setGovKeyWithAggKey,
        cf.GOVERNOR_2,
    )

    checkCurrentKeys(
        cf, AGG_SIGNER_1.getPubDataWith0x(), cf.GOVERNOR_2, cf.COMMUNITY_KEY
    )

    assert tx.events["GovKeySetByAggKey"][0].values() == [cf.GOVERNOR, cf.GOVERNOR_2]


def setCommKeyWithAggKey_test(cf):
    checkCurrentKeys(cf, AGG_SIGNER_1.getPubDataWith0x(), cf.GOVERNOR, cf.COMMUNITY_KEY)

    tx = signed_call_cf(
        cf,
        cf.keyManager.setCommKeyWithAggKey,
        cf.COMMUNITY_KEY_2,
    )

    checkCurrentKeys(
        cf, AGG_SIGNER_1.getPubDataWith0x(), cf.GOVERNOR, cf.COMMUNITY_KEY_2
    )

    assert tx.events["CommKeySetByAggKey"][0].values() == [
        cf.COMMUNITY_KEY,
        cf.COMMUNITY_KEY_2,
    ]


def setCommKeyWithCommKey_test(cf):
    checkCurrentKeys(cf, AGG_SIGNER_1.getPubDataWith0x(), cf.GOVERNOR, cf.COMMUNITY_KEY)

    tx = cf.keyManager.setCommKeyWithCommKey(
        cf.COMMUNITY_KEY_2, {"from": cf.COMMUNITY_KEY}
    )

    checkCurrentKeys(
        cf, AGG_SIGNER_1.getPubDataWith0x(), cf.GOVERNOR, cf.COMMUNITY_KEY_2
    )

    assert tx.events["CommKeySetByCommKey"][0].values() == [
        cf.COMMUNITY_KEY,
        cf.COMMUNITY_KEY_2,
    ]


def checkCurrentKeys(cf, aggKey, govKey, commkey):
    assert cf.keyManager.getAggregateKey() == aggKey
    assert cf.keyManager.getGovernanceKey() == govKey
    assert cf.keyManager.getCommunityKey() == commkey


def canConsumeKeyNonce_test(cf, signer):
    sigData = signer.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
    cf.keyManager.consumeKeyNonce(sigData, cleanHexStr(sigData[2]))


def canConsumeKeyNonce_rev_test(cf, signer):
    sigData = signer.getSigData(JUNK_HEX_PAD, cf.keyManager.address)
    with reverts(REV_MSG_SIG):
        cf.keyManager.consumeKeyNonce(sigData, cleanHexStr(sigData[2]))


# Hypothesis/brownie doesn't allow you to specifically include values when generating random
# inputs through @given, so this is a common fcn that can be used for `test_claim` and
# similar tests that test specific desired values
# Can't put the if conditions for `amount` in this fcn like in test_claim because
# it's we need to accomodate already having a tx because it's best to test
# `stakedMin` directly
def stakeTest(cf, prevTotal, nodeID, minStake, tx, amount, returnAddr):
    assert (
        cf.flip.balanceOf(cf.stakeManager)
        == prevTotal + amount + STAKEMANAGER_INITIAL_BALANCE
    )
    assert tx.events["Staked"][0].values() == [nodeID, amount, tx.sender, returnAddr]
    assert cf.stakeManager.getMinimumStake() == minStake


# Hypothesis/brownie doesn't allow you to specifically include values when generating random
# inputs through @given, so this is a common fcn that can be used for `test_claim` and
# similar tests that test specific desired values
def registerClaimTest(cf, stakeManager, nodeID, minStake, amount, receiver, expiryTime):
    prevReceiverBal = cf.flip.balanceOf(receiver)
    prevStakeManBal = cf.flip.balanceOf(stakeManager)

    tx = signed_call_cf(
        cf,
        stakeManager.registerClaim,
        nodeID,
        amount,
        receiver,
        expiryTime,
    )

    startTime = tx.timestamp + CLAIM_DELAY
    # Check things that should've changed
    assert stakeManager.getPendingClaim(nodeID) == (
        amount,
        receiver,
        startTime,
        expiryTime,
    )
    assert tx.events["ClaimRegistered"][0].values() == (
        nodeID,
        amount,
        receiver,
        startTime,
        expiryTime,
    )
    # Check things that shouldn't have changed
    assert cf.flip.balanceOf(receiver) == prevReceiverBal
    assert cf.flip.balanceOf(stakeManager) == prevStakeManBal
    assert stakeManager.getMinimumStake() == minStake


# Function used to do function calls that require a signature
def signed_call_cf(cf, fcn, *args, **kwargs):
    # Get default values
    sender = kwargs.get("sender", cf.deployer)
    keyManager = kwargs.get("keyManager", cf.keyManager)
    signer = kwargs.get("signer", AGG_SIGNER_1)

    return signed_call(keyManager, fcn, signer, sender, *args)


# Another separate signed call to make tests less verbose
def signed_call_km(keyManager, fcn, *args, **kwargs):
    # Get default values
    # Workaround because kwargs.get("sender", kwargs.get("cf").deployer) doesn't work if there is no "cf" key
    sender = kwargs.get("sender") if "sender" in kwargs else kwargs.get("cf").deployer
    signer = kwargs.get("signer", AGG_SIGNER_1)

    return signed_call(keyManager, fcn, signer, sender, *args)


def signed_call(keyManager, fcn, signer, sender, *args):
    # Sign the tx without a msgHash or sig
    callDataNoSig = fcn.encode_input(agg_null_sig(keyManager.address, chain.id), *args)
    return fcn(
        signer.getSigDataWithNonces(callDataNoSig, nonces, keyManager.address),
        *args,
        {"from": sender},
    )


# Assumption that all the parameters are the same length. Craft the TransferParams array.
def craftTransferParamsArray(tokens, recipients, amounts):
    length = len(tokens)
    args = []
    for index in range(length):
        args.append([tokens[index], recipients[index], amounts[index]])
    return args


# Assumption that all the parameters are the same length. Craft the FetchParams array.
def craftFetchParamsArray(swapIDs, tokens):
    length = len(tokens)
    args = []
    for index in range(length):
        args.append([swapIDs[index], tokens[index]])
    return args
