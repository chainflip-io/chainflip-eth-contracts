from consts import *
from brownie import reverts


def test_suspend(cf):
    cf.stakeManager.suspend({"from": cf.GOVERNOR})
    assert cf.stakeManager.suspended() == True


def test_suspend_rev_notGovernor(cf):
    initialValue = cf.stakeManager.suspended()
    with reverts(REV_MSG_STAKEMAN_GOVERNOR):
        cf.stakeManager.suspend({"from": cf.ALICE})
    assert cf.stakeManager.suspended() == initialValue


def test_resume(cf):
    cf.stakeManager.resume({"from": cf.GOVERNOR})
    assert cf.stakeManager.suspended() == False


def test_resume_rev_notGovernor(cf):
    initialValue = cf.stakeManager.suspended()
    with reverts(REV_MSG_STAKEMAN_GOVERNOR):
        cf.stakeManager.resume({"from": cf.ALICE})
    assert cf.stakeManager.suspended() == initialValue


def test_suspend_resume(cf):
    test_suspend(cf)
    test_resume(cf)
