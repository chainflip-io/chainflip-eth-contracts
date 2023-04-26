from consts import *
from brownie.test import given, strategy
from brownie import reverts, chain
from utils import *
from shared_tests import *


def update_issuer(cf, new_issuer):
    signed_call_cf(cf, cf.stakeManager.updateFlipIssuer, new_issuer)


@given(st_issuer=strategy("address"))
def test_updateIssuer(cf, st_issuer):
    assert cf.flip.issuer() == cf.stakeManager.address
    update_issuer(cf, st_issuer)
    assert cf.flip.issuer() == st_issuer


@given(st_sender=strategy("address"))
def test_revIssuer(cf, st_sender):
    assert cf.flip.issuer() == cf.stakeManager.address
    with reverts(REV_MSG_FLIP_ISSUER):
        cf.flip.updateIssuer(NON_ZERO_ADDR, {"from": st_sender})
