from consts import *
from brownie import reverts


def test_suspend(cf):
    cf.stakeManager.suspend({"from": cf.GOVERNOR})
    assert cf.stakeManager.getSuspendedState() == True


def test_suspend_rev_notGovernor(cf):
    initialValue = cf.stakeManager.getSuspendedState()
    with reverts(REV_MSG_STAKEMAN_GOVERNOR):
        cf.stakeManager.suspend({"from": cf.ALICE})
    assert cf.stakeManager.getSuspendedState() == initialValue


def test_resume(cf):
    suspended = cf.stakeManager.getSuspendedState()
    if suspended:
        cf.stakeManager.resume({"from": cf.GOVERNOR})
    else:
        with reverts(REV_MSG_STAKEMAN_NOT_SUSPENDED):
            cf.stakeManager.resume({"from": cf.GOVERNOR})

    assert cf.stakeManager.getSuspendedState() == False


def test_resume_rev_notGovernor(cf):
    initialValue = cf.stakeManager.getSuspendedState()
    with reverts(REV_MSG_STAKEMAN_GOVERNOR):
        cf.stakeManager.resume({"from": cf.ALICE})
    assert cf.stakeManager.getSuspendedState() == initialValue


def test_suspend_resume(cf):
    test_suspend(cf)
    test_resume(cf)
