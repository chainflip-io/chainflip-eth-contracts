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
        cls.sm = cfDeploy.stakeManager
        cls.f = cfDeploy.flip


@pytest.fixture
def BaseStateMachine():
    yield _BaseStateMachine