from consts import *
from shared_tests import *
from brownie import network
from brownie.test import given, strategy
from deploy import deploy_new_vault, deploy_new_stakeManager


@given(
    st_pubKeyX=strategy("uint256", exclude=0, max_value=5**76),  # > (~HALF_Q)
    st_pubKeyYParity=strategy("uint8", exclude=0),
    st_govKey=strategy("address", exclude=0),
    st_commKey=strategy("address", exclude=0),
    st_minStake=strategy("uint256", exclude=0),
    st_initSupply=strategy(
        "uint256", min_value=INIT_SUPPLY / 2, max_value=INIT_SUPPLY * 10
    ),
    st_numGenesisValidators=strategy(
        "uint256",
        min_value=NUM_GENESIS_VALIDATORS - 3,
        max_value=NUM_GENESIS_VALIDATORS * 10,
    ),
    st_genesisStake=strategy(
        "uint256", min_value=GENESIS_STAKE / 2, max_value=GENESIS_STAKE * 2
    ),
)
def test_deployer_constructor(
    DeployerContract,
    FLIP,
    Vault,
    KeyManager,
    StakeManager,
    addrs,
    st_pubKeyX,
    st_pubKeyYParity,
    st_govKey,
    st_commKey,
    st_minStake,
    st_initSupply,
    st_numGenesisValidators,
    st_genesisStake,
):
    network.priority_fee("1 gwei")

    deployerContract = addrs.DEPLOYER.deploy(
        DeployerContract,
        [st_pubKeyX, st_pubKeyYParity],
        st_govKey,
        st_commKey,
        st_minStake,
        st_initSupply,
        st_numGenesisValidators,
        st_genesisStake,
    )

    vault = Vault.at(deployerContract.vault())
    flip = FLIP.at(deployerContract.flip())
    keyManager = KeyManager.at(deployerContract.keyManager())
    stakeManager = StakeManager.at(deployerContract.stakeManager())

    check_contracts_state(
        st_pubKeyX,
        st_pubKeyYParity,
        st_govKey,
        st_commKey,
        st_minStake,
        st_initSupply,
        st_numGenesisValidators,
        st_genesisStake,
        vault,
        flip,
        keyManager,
        stakeManager,
    )


@given(
    st_govKey=strategy("address", exclude=0),
    st_commKey=strategy("address", exclude=0),
    st_initSupply=strategy(
        "uint256", min_value=INIT_SUPPLY / 2, max_value=INIT_SUPPLY * 10
    ),
    st_numGenesisValidators=strategy(
        "uint256",
        min_value=NUM_GENESIS_VALIDATORS - 3,
        max_value=NUM_GENESIS_VALIDATORS * 10,
    ),
    st_genesisStake=strategy(
        "uint256", min_value=GENESIS_STAKE / 2, max_value=GENESIS_STAKE * 2
    ),
    st_sender=strategy("address"),
)
def test_upgrader_constructor(
    DeployerContract,
    DeployerStakeManager,
    FLIP,
    Vault,
    KeyManager,
    StakeManager,
    addrs,
    st_govKey,
    st_commKey,
    st_initSupply,
    st_numGenesisValidators,
    st_genesisStake,
    st_sender,
):
    network.priority_fee("1 gwei")

    st_pubKeyX = AGG_SIGNER_1.getPubData()[0]
    st_pubKeyYParity = AGG_SIGNER_1.getPubData()[1]

    # Deploy with the default AGG_SIG so we can upgrade it later
    deployerContract = addrs.DEPLOYER.deploy(
        DeployerContract,
        AGG_SIGNER_1.getPubData(),
        st_govKey,
        st_commKey,
        MIN_STAKE,
        st_initSupply,
        st_numGenesisValidators,
        st_genesisStake,
    )

    vault = Vault.at(deployerContract.vault())
    flip = FLIP.at(deployerContract.flip())
    keyManager = KeyManager.at(deployerContract.keyManager())
    stakeManager = StakeManager.at(deployerContract.stakeManager())

    new_vault = deploy_new_vault(addrs.DEPLOYER, Vault, KeyManager, keyManager.address)

    (deployerStakeManager, new_stakeManager) = deploy_new_stakeManager(
        addrs.DEPLOYER,
        KeyManager,
        StakeManager,
        FLIP,
        DeployerStakeManager,
        keyManager.address,
        flip.address,
    )

    assert deployerStakeManager.keyManager() == keyManager.address
    assert deployerStakeManager.flip() == flip.address
    assert deployerStakeManager.stakeManager() == new_stakeManager.address

    # Check the old contracts have remained untouched
    check_contracts_state(
        st_pubKeyX,
        st_pubKeyYParity,
        st_govKey,
        st_commKey,
        MIN_STAKE,
        st_initSupply,
        st_numGenesisValidators,
        st_genesisStake,
        vault,
        flip,
        keyManager,
        stakeManager,
    )

    args = [
        JUNK_HEX,
        flip.balanceOf(stakeManager.address),
        new_stakeManager.address,
        getChainTime() + (2 * CLAIM_DELAY),
    ]

    # Manually transfer FLIP funds.
    signed_call(keyManager, stakeManager.registerClaim, AGG_SIGNER_1, st_sender, *args)

    # Execute claim
    chain.sleep(CLAIM_DELAY)
    stakeManager.executeClaim(JUNK_HEX, {"from": st_sender})

    check_contracts_state(
        st_pubKeyX,
        st_pubKeyYParity,
        st_govKey,
        st_commKey,
        MIN_STAKE,
        st_initSupply,
        st_numGenesisValidators,
        st_genesisStake,
        new_vault,
        flip,
        keyManager,
        new_stakeManager,
    )


def check_contracts_state(
    st_pubKeyX,
    st_pubKeyYParity,
    st_govKey,
    st_commKey,
    st_minStake,
    st_initSupply,
    st_numGenesisValidators,
    st_genesisStake,
    vault,
    flip,
    keyManager,
    stakeManager,
):
    assert keyManager.getAggregateKey() == [st_pubKeyX, st_pubKeyYParity]
    assert keyManager.getGovernanceKey() == st_govKey
    assert keyManager.getCommunityKey() == st_commKey

    assert stakeManager.getMinimumStake() == st_minStake
    assert stakeManager.getFLIP() == flip.address
    assert stakeManager.getKeyManager() == keyManager.address

    assert flip.getKeyManager() == keyManager.address
    assert flip.totalSupply() == st_initSupply
    assert flip.balanceOf(stakeManager) == st_numGenesisValidators * st_genesisStake
    assert (
        flip.balanceOf(st_govKey)
        == st_initSupply - st_numGenesisValidators * st_genesisStake
    )

    assert vault.getKeyManager() == keyManager.address
