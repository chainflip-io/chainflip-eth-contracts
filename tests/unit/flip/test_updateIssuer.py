from consts import *
from brownie.test import given, strategy
from brownie import reverts
from utils import *
from shared_tests import *

# NOTE: We want to test updateIssuer in isolation from the rest of the contracts
# so we will deploy the FLIP contract separately and set an EOA as the issuer.


def deploy_flip(cf, FLIP, issuer):
    return FLIP.deploy(
        INIT_SUPPLY,
        cf.numGenesisValidators,
        cf.genesisStake,
        cf.ALICE,
        cf.BOB,
        issuer,
        {"from": cf.CHARLIE},
    )


@given(st_issuer=strategy("address"))
def test_updateIssuer_st(cf, st_issuer, FLIP):
    flip = deploy_flip(cf, FLIP, cf.ALICE)
    assert flip.getIssuer() == cf.ALICE
    flip.updateIssuer(st_issuer, {"from": cf.ALICE})
    assert flip.getIssuer() == st_issuer


def test_updateIssuer_ref(cf, FLIP):
    flip = deploy_flip(cf, FLIP, cf.BOB)
    assert flip.getIssuer() == cf.BOB
    flip.updateIssuer(cf.stateChainGateway.address, {"from": cf.BOB})
    assert flip.getIssuer() == cf.stateChainGateway.address


@given(st_sender=strategy("address"))
def test_revIssuer(cf, st_sender):
    assert cf.flip.getIssuer() == cf.stateChainGateway.address
    with reverts(REV_MSG_FLIP_ISSUER):
        cf.flip.updateIssuer(NON_ZERO_ADDR, {"from": st_sender})
