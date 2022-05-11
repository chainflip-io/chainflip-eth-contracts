from consts import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy
from utils import *


@given(
    st_sender=strategy("address"),
)
def test_setGovKeyWithAggKey(cf, st_sender):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR
    assert cf.keyManager.getCommunityKey() == cf.communityKey

    callDataNoSig = cf.keyManager.setGovKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), st_sender
    )

    tx = cf.keyManager.setGovKeyWithAggKey(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        st_sender,
        {"from": cf.ALICE},
    )

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == st_sender
    assert cf.keyManager.getCommunityKey() == cf.communityKey

    assert tx.events["GovKeySetByAggKey"][0].values() == [
        cf.GOVERNOR,
        st_sender,
    ]


def test_setGovKeyWithAggKey_rev(cf):
    callDataNoSig = cf.keyManager.setGovKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ZERO_ADDR
    )

    with reverts(REV_MSG_NZ_ADDR):
        cf.keyManager.setGovKeyWithAggKey(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            ZERO_ADDR,
            {"from": cf.ALICE},
        )
