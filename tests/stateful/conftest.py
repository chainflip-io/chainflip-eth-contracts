import pytest


class _BaseStateMachine:

    """
    https://eth-brownie.readthedocs.io/en/stable/tests-hypothesis-stateful.html
    This base state machine class contains initialization of the system that all
    other tests need to start at (simple deployment).
    """

    def __init__(cls, a, cfDeploy):
        cls.a = a
        cls.km = cfDeploy.keyManager
        cls.v = cfDeploy.vault
        cls.sm = cfDeploy.stateChainGateway
        cls.f = cfDeploy.flip
        cls.deployerContract = cfDeploy.deployerContract

        cls.COMMUNITY_KEY = cfDeploy.communityKey
        cls.COMMUNITY_KEY_2 = a[7]


@pytest.fixture
def BaseStateMachine():
    yield _BaseStateMachine
