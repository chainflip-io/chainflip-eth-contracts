from consts import *
from brownie import network
from brownie.test import given, strategy


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
def test_constructor(
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

    assert keyManager.getAggregateKey() == [st_pubKeyX, st_pubKeyYParity]
    assert keyManager.getGovernanceKey() == st_govKey
    assert keyManager.getCommunityKey() == st_commKey

    assert stakeManager.getMinimumStake() == st_minStake
    assert stakeManager.getFLIP() == flip.address

    assert flip.totalSupply() == st_initSupply
    assert flip.balanceOf(stakeManager) == st_numGenesisValidators * st_genesisStake
    assert (
        flip.balanceOf(st_govKey)
        == st_initSupply - st_numGenesisValidators * st_genesisStake
    )

    assert keyManager.canConsumeKeyNonceSet() == True
    assert keyManager.getNumberWhitelistedAddresses() == 3
    assert keyManager.canConsumeKeyNonce(vault.address) == True
    assert keyManager.canConsumeKeyNonce(stakeManager.address) == True
    assert keyManager.canConsumeKeyNonce(flip.address) == True
    assert keyManager.canConsumeKeyNonce(keyManager.address) == False
