from utils import *
import umbral
from umbral import pre, keys, signing


umbral.config.set_default_curve()

# Fcns return a list instead of a tuple since they need to be modified
# for some tests (e.g. to make them revert)
class Signer():

    Q = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141"
    Q_INT = int(Q, 16)
    HALF_Q_INT = (Q_INT >> 1) + 1


    def __init__(self, privKeyHex, kHex, keyIDNum):
        self.privKeyHex = privKeyHex
        self.privKey = keys.UmbralPrivateKey.from_bytes(bytes.fromhex(privKeyHex))
        self.privKeyInt = int(self.privKeyHex, 16)

        self.pubKey = self.privKey.get_pubkey()
        self.pubKeyX = self.pubKey.to_bytes()[1:]
        self.pubKeyXHex = cleanHexStr(self.pubKeyX)
        self.pubKeyXInt = int(self.pubKeyXHex, 16)
        
        self.pubKeyYPar = 0 if cleanHexStr(self.pubKey.to_bytes()[:1]) == "02" else 1
        self.pubKeyYParHex = "00" if self.pubKeyYPar == 0 else "01"

        self.k = keys.UmbralPrivateKey.from_bytes(bytes.fromhex(kHex))
        self.kHex = kHex
        self.kInt = int(self.kHex, 16)
        kTimesG = self.k.get_pubkey()
        kTimesGPub = kTimesG.to_bytes(is_compressed=False)[1:]
        self.kTimesGAddressHex = cleanHexStr(web3.toChecksumAddress(cleanHexStr(web3.keccak(kTimesGPub)[-20:])))

        self.keyIDNum = keyIDNum


    @classmethod
    def priv_key_to_pubX_int(cls, privKey):
        pubKey = privKey.get_pubkey()
        pubKeyX = pubKey.to_bytes()[1:]
        return int(cleanHexStr(pubKeyX), 16)


    @classmethod
    def gen_key(cls):
        key = keys.UmbralPrivateKey.gen_key()
        while cls.priv_key_to_pubX_int(key) >= cls.HALF_Q_INT:
            key = keys.UmbralPrivateKey.gen_key()
        
        return key


    @classmethod
    def gen_key_hex(cls):
        return cls.gen_key().to_bytes().hex()
    

    @classmethod
    def gen_signer(cls):
        privKeyHex = cls.gen_key_hex()
        kHex = keys.UmbralPrivateKey.gen_key().to_bytes().hex()
        return cls(privKeyHex, kHex, -1)



    def getPubData(self):
        return [self.pubKeyXInt, self.pubKeyYPar, self.kTimesGAddressHex]
    

    def getPubDataWith0x(self):
        return [self.pubKeyXInt, self.pubKeyYPar, "0x" + self.kTimesGAddressHex]


    def getSigData(self, msgToHash):
        msgHashHex = cleanHexStr(web3.keccak(hexstr=msgToHash))
        e = web3.keccak(hexstr=(cleanHexStr(self.pubKeyX) + self.pubKeyYParHex + msgHashHex + self.kTimesGAddressHex))

        eInt = int(cleanHexStr(e), 16)

        s = (self.kInt - (self.privKeyInt * eInt)) % self.Q_INT
        s = s + self.Q_INT if s < 0 else s

        return [int(msgHashHex, 16), s]
