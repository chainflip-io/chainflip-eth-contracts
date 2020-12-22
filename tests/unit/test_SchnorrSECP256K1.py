from consts import *


MSG_HASH_HEX = "18f224412c876d8efb2a3fa670837b5ad1347120363c2b310653f610d382729b"

def test_verifySignature(a, SchnorrSECP256K1):
    schnorr = a[0].deploy(SchnorrSECP256K1)
    assert schnorr.verifySignature(*AGG_SIGNER_1.getPubData(), *AGG_SIGNER_1.getSigData(MSG_HASH_HEX))
