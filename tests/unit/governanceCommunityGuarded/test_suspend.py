from consts import *
from brownie import reverts


def test_suspend(cf):
    suspend(cf, cf.stateChainGateway)
    suspend(cf, cf.vault)


def test_suspend_rev_notGovernor(cf):
    suspend_rev_notGovernor(cf, cf.stateChainGateway)
    suspend_rev_notGovernor(cf, cf.vault)


def test_resume(cf):
    resume(cf, cf.stateChainGateway)
    resume(cf, cf.vault)


def test_resume_rev_notGovernor(cf):
    resume_rev_notGovernor(cf, cf.stateChainGateway)
    resume_rev_notGovernor(cf, cf.vault)


def test_suspend_resume(cf):
    test_suspend(cf)
    test_resume(cf)


def suspend(cf, governanceCommunityGuarded):
    tx = governanceCommunityGuarded.suspend({"from": cf.GOVERNOR})
    assert governanceCommunityGuarded.getSuspendedState() == True
    assert tx.events["Suspended"][0].values()[0] == True


def suspend_rev_notGovernor(cf, governanceCommunityGuarded):
    initialValue = governanceCommunityGuarded.getSuspendedState()
    with reverts(REV_MSG_GOV_GOVERNOR):
        governanceCommunityGuarded.suspend({"from": cf.ALICE})
    assert governanceCommunityGuarded.getSuspendedState() == initialValue


def resume(cf, governanceCommunityGuarded):
    suspended = governanceCommunityGuarded.getSuspendedState()
    if suspended:
        tx = governanceCommunityGuarded.resume({"from": cf.GOVERNOR})
        assert tx.events["Suspended"][0].values()[0] == False
    else:
        with reverts(REV_MSG_GOV_NOT_SUSPENDED):
            governanceCommunityGuarded.resume({"from": cf.GOVERNOR})

    assert governanceCommunityGuarded.getSuspendedState() == False


def resume_rev_notGovernor(cf, governanceCommunityGuarded):
    initialValue = governanceCommunityGuarded.getSuspendedState()
    with reverts(REV_MSG_GOV_GOVERNOR):
        governanceCommunityGuarded.resume({"from": cf.ALICE})
    assert governanceCommunityGuarded.getSuspendedState() == initialValue
