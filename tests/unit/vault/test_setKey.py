from utils import *
from crypto import *
from consts import *


def test_setAggKeyByAggKey(a, vault):
    callDataNoSig = vault.setAggKeyByAggKey.encode_input(*AGG_SIGNER_2.getPubData(), "", "")
    tx = vault.setAggKeyByAggKey(*AGG_SIGNER_2.getPubData(), *AGG_SIGNER_1.getSigData(callDataNoSig))
