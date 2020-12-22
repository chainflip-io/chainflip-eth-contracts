from utils import *
import umbral
from umbral import pre, keys, signing


umbral.config.set_default_curve()

class Signer():

    Q = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141"
    Q_INT = int(Q, 16)


    def __init__(self, privKeyHex, kHex):
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
        self.kTimesGAddressHex = cleanHexStr(w3.toChecksumAddress(cleanHexStr(w3.keccak(kTimesGPub)[-20:])))


    def getPubData(self):
        return self.pubKeyXInt, self.pubKeyYPar, self.kTimesGAddressHex


    def getSigData(self, msgToHash):
        msgHashHex = cleanHexStr(w3.keccak(hexstr=msgToHash))
        e = w3.keccak(hexstr=(cleanHexStr(self.pubKeyX) + self.pubKeyYParHex + msgHashHex + self.kTimesGAddressHex))

        eInt = int(cleanHexStr(e), 16)

        s = (self.kInt - (self.privKeyInt * eInt)) % self.Q_INT
        s = s + self.Q_INT if s < 0 else s

        return int(msgHashHex, 16), s
