def test_constructor(cf):
    assert cf.vault.getKeyManager() == cf.keyManager.address
