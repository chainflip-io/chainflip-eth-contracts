from consts import *
from brownie import reverts
from test_governanceCommuityGuarded import getgovernanceCommunityGuardedList


def test_suspend(cf):
    governanceCommunityGuardedList = getgovernanceCommunityGuardedList(cf)
    for governanceCommunityGuarded in governanceCommunityGuardedList:
        governanceCommunityGuarded.suspend({"from": cf.GOVERNOR})
        assert governanceCommunityGuarded.getSuspendedState() == True


def test_suspend_rev_notGovernor(cf):
    governanceCommunityGuardedList = getgovernanceCommunityGuardedList(cf)
    for governanceCommunityGuarded in governanceCommunityGuardedList:
        initialValue = governanceCommunityGuarded.getSuspendedState()
        with reverts(REV_MSG_GOV_GOVERNOR):
            governanceCommunityGuarded.suspend({"from": cf.ALICE})
        assert governanceCommunityGuarded.getSuspendedState() == initialValue


def test_resume(cf):
    governanceCommunityGuardedList = getgovernanceCommunityGuardedList(cf)
    for governanceCommunityGuarded in governanceCommunityGuardedList:
        suspended = governanceCommunityGuarded.getSuspendedState()
        if suspended:
            governanceCommunityGuarded.resume({"from": cf.GOVERNOR})
        else:
            with reverts(REV_MSG_GOV_NOT_SUSPENDED):
                governanceCommunityGuarded.resume({"from": cf.GOVERNOR})

        assert governanceCommunityGuarded.getSuspendedState() == False


def test_resume_rev_notGovernor(cf):
    governanceCommunityGuardedList = getgovernanceCommunityGuardedList(cf)
    for governanceCommunityGuarded in governanceCommunityGuardedList:
        initialValue = governanceCommunityGuarded.getSuspendedState()
        with reverts(REV_MSG_GOV_GOVERNOR):
            governanceCommunityGuarded.resume({"from": cf.ALICE})
        assert governanceCommunityGuarded.getSuspendedState() == initialValue


def test_suspend_resume(cf):
    test_suspend(cf)
    test_resume(cf)
