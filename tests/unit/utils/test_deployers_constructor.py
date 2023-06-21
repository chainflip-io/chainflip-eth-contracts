from consts import *
from shared_tests import *
from brownie import network
from brownie.test import given, strategy
from deploy import deploy_new_vault, deploy_new_stateChainGateway


@given(
    st_pubKeyX=strategy("uint256", exclude=0, max_value=5**76),  # > (~HALF_Q)
    st_pubKeyYParity=strategy("uint8", exclude=0),
    st_govKey=strategy("address", exclude=0),
    st_commKey=strategy("address", exclude=0),
    st_minFunding=strategy("uint256", exclude=0),
    st_redemptionDelay=strategy("uint48", exclude=0),
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
    StateChainGateway,
    addrs,
    st_pubKeyX,
    st_pubKeyYParity,
    st_govKey,
    st_commKey,
    st_minFunding,
    st_redemptionDelay,
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
        st_minFunding,
        st_redemptionDelay,
        st_initSupply,
        st_numGenesisValidators,
        st_genesisStake,
    )

    vault = Vault.at(deployerContract.vault())
    flip = FLIP.at(deployerContract.flip())
    keyManager = KeyManager.at(deployerContract.keyManager())
    stateChainGateway = StateChainGateway.at(deployerContract.stateChainGateway())

    check_contracts_state(
        st_pubKeyX,
        st_pubKeyYParity,
        st_govKey,
        st_commKey,
        st_minFunding,
        st_redemptionDelay,
        st_initSupply,
        st_numGenesisValidators,
        st_genesisStake,
        vault,
        flip,
        keyManager,
        stateChainGateway,
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
    DeployerStateChainGateway,
    FLIP,
    Vault,
    KeyManager,
    StateChainGateway,
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
        MIN_FUNDING,
        REDEMPTION_DELAY,
        st_initSupply,
        st_numGenesisValidators,
        st_genesisStake,
    )

    vault = Vault.at(deployerContract.vault())
    flip = FLIP.at(deployerContract.flip())
    keyManager = KeyManager.at(deployerContract.keyManager())
    stateChainGateway = StateChainGateway.at(deployerContract.stateChainGateway())

    new_vault = deploy_new_vault(addrs.DEPLOYER, Vault, KeyManager, keyManager.address)

    (deployerStateChainGateway, new_stateChainGateway) = deploy_new_stateChainGateway(
        addrs.DEPLOYER,
        KeyManager,
        StateChainGateway,
        FLIP,
        DeployerStateChainGateway,
        keyManager.address,
        flip.address,
        MIN_FUNDING,
        REDEMPTION_DELAY,
    )

    assert deployerStateChainGateway.keyManager() == keyManager.address
    assert deployerStateChainGateway.flip() == flip.address
    assert (
        deployerStateChainGateway.stateChainGateway() == new_stateChainGateway.address
    )

    # Check the old contracts have remained untouched
    check_contracts_state(
        st_pubKeyX,
        st_pubKeyYParity,
        st_govKey,
        st_commKey,
        MIN_FUNDING,
        REDEMPTION_DELAY,
        st_initSupply,
        st_numGenesisValidators,
        st_genesisStake,
        vault,
        flip,
        keyManager,
        stateChainGateway,
    )

    args = [
        JUNK_HEX,
        flip.balanceOf(stateChainGateway.address),
        new_stateChainGateway.address,
        getChainTime() + (2 * REDEMPTION_DELAY),
    ]

    # Manually transfer FLIP funds.
    signed_call(
        keyManager, stateChainGateway.registerRedemption, AGG_SIGNER_1, st_sender, *args
    )

    # Execute redemption
    chain.sleep(REDEMPTION_DELAY)
    stateChainGateway.executeRedemption(JUNK_HEX, {"from": st_sender})

    check_contracts_state(
        st_pubKeyX,
        st_pubKeyYParity,
        st_govKey,
        st_commKey,
        MIN_FUNDING,
        REDEMPTION_DELAY,
        st_initSupply,
        st_numGenesisValidators,
        st_genesisStake,
        new_vault,
        flip,
        keyManager,
        new_stateChainGateway,
    )


def check_contracts_state(
    st_pubKeyX,
    st_pubKeyYParity,
    st_govKey,
    st_commKey,
    st_minFunding,
    st_redemptionDelay,
    st_initSupply,
    st_numGenesisValidators,
    st_genesisStake,
    vault,
    flip,
    keyManager,
    stateChainGateway,
):
    assert keyManager.getAggregateKey() == [st_pubKeyX, st_pubKeyYParity]
    assert keyManager.getGovernanceKey() == st_govKey
    assert keyManager.getCommunityKey() == st_commKey

    assert stateChainGateway.getMinimumFunding() == st_minFunding
    assert stateChainGateway.getFLIP() == flip.address
    assert stateChainGateway.getKeyManager() == keyManager.address
    assert stateChainGateway.REDEMPTION_DELAY() == st_redemptionDelay

    assert flip.totalSupply() == st_initSupply
    assert (
        flip.balanceOf(stateChainGateway) == st_numGenesisValidators * st_genesisStake
    )
    assert (
        flip.balanceOf(st_govKey)
        == st_initSupply - st_numGenesisValidators * st_genesisStake
    )

    assert vault.getKeyManager() == keyManager.address
