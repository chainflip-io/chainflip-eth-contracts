import pytest
from deploy import deploy_initial_ChainFlip_contracts


class _BaseStateMachine:

    """
    This base state machine class contains initialization and invariant
    methods that are shared across multiple stateful tests.
    """

    def __init__(cls, a, KeyManager, Vault, StakeManager, FLIP):
        cls.a = a
        cf = deploy_initial_ChainFlip_contracts(a[0], KeyManager, Vault, StakeManager, FLIP)
        cls.km = cf.keyManager
        cls.v = cf.vault
        cls.sm = cf.stakeManager
        cls.f = cf.flip

    # def invariant_balances(self):


@pytest.fixture
def BaseStateMachine():
    yield _BaseStateMachine