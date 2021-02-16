import pytest
from deploy import deploy_initial_ChainFlip_contracts


class _BaseStateMachine:

    """
    This base state machine class contains initialization and invariant
    methods that are shared across multiple stateful tests.
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