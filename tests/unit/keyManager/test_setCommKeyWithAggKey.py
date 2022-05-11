from consts import *
from brownie import reverts, chain, web3
from brownie.test import given, strategy
from utils import *


@given(
    st_sender=strategy("address"),
)
def test_setCommKeyWithAggKey(cf, st_sender):
    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR
    assert cf.keyManager.getCommunityKey() == cf.communityKey

    callDataNoSig = cf.keyManager.setCommKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), st_sender
    )

    tx = cf.keyManager.setCommKeyWithAggKey(
        AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
        st_sender,
        {"from": cf.ALICE},
    )

    assert cf.keyManager.getAggregateKey() == AGG_SIGNER_1.getPubDataWith0x()
    assert cf.keyManager.getGovernanceKey() == cf.GOVERNOR
    assert cf.keyManager.getCommunityKey() == st_sender

    assert tx.events["CommKeySetByAggKey"][0].values() == [
        cf.communityKey,
        st_sender,
    ]


def test_setCommKeyWithAggKey_rev(cf):
    callDataNoSig = cf.keyManager.setCommKeyWithAggKey.encode_input(
        agg_null_sig(cf.keyManager.address, chain.id), ZERO_ADDR
    )

    with reverts(REV_MSG_NZ_ADDR):
        cf.keyManager.setCommKeyWithAggKey(
            AGG_SIGNER_1.getSigData(callDataNoSig, cf.keyManager.address),
            ZERO_ADDR,
            {"from": cf.ALICE},
        )
