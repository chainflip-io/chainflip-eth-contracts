from utils import *
import umbral
from umbral import pre, keys, signing
from py_ecc.secp256k1 import secp256k1

umbral.config.set_default_curve()

# Fcns return a list instead of a tuple since they need to be modified
# for some tests (e.g. to make them revert)
class Signer():

    Q = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141"
    Q_INT = int(Q, 16)
    HALF_Q_INT = (Q_INT >> 1) + 1


    def __init__(self, privKeyHex, keyID, nonces):
        self.privKeyHex = privKeyHex
        self.privKey = keys.UmbralPrivateKey.from_bytes(bytes.fromhex(privKeyHex))
        self.privKeyInt = int(self.privKeyHex, 16)

        self.pubKey = self.privKey.get_pubkey()
        self.pubKeyX = self.pubKey.to_bytes()[1:]
        self.pubKeyXHex = cleanHexStr(self.pubKeyX)
        self.pubKeyXInt = int(self.pubKeyXHex, 16)

        self.pubKeyYPar = 0 if cleanHexStr(self.pubKey.to_bytes()[:1]) == "02" else 1
        self.pubKeyYParHex = "00" if self.pubKeyYPar == 0 else "01"

        self.keyID = keyID
        self.nonces = nonces


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
    def gen_signer(cls, keyID, nonces):
        privKeyHex = cls.gen_key_hex()
        kHex = keys.UmbralPrivateKey.gen_key().to_bytes().hex()
        return cls(privKeyHex, kHex, keyID, nonces)


    def getPubData(self):
        return [self.pubKeyXInt, self.pubKeyYPar]


    def getPubDataWith0x(self):
        return [self.pubKeyXInt, self.pubKeyYPar]


    def getSigData(self, msgToHash):
        return self.getSigDataWithKeyID(msgToHash, self.keyID)

    def getSigDataWithKeyID(self, msgToHash, keyID):
        msgHashHex = cleanHexStr(web3.keccak(hexstr=msgToHash))

        # Pick a "random" nonce (k)
        k = int(web3.keccak(hexstr=msgHashHex).hex(), 16)
        kTimesG = tuple(secp256k1.multiply(secp256k1.G, k))

        # Get the x and y ordinate of our K*g value
        kTimesGXInt = kTimesG[0] # bigint
        kTimesGYParityInt = kTimesG[1] # bigint
        kTimesGXBytes = (kTimesGXInt).to_bytes(32, byteorder='big')
        kTimesGYParityBytes = (kTimesGYParityInt).to_bytes(32, byteorder='big')
        kTimesGConcat = kTimesGXBytes + kTimesGYParityBytes

        # kTime
        k256 = web3.keccak(kTimesGConcat)
        nonceTimesGeneratorAddress = web3.toChecksumAddress(cleanHexStr(k256)[-40:])
        challengeEncodedPacked = cleanHexStrPad(self.pubKeyX) + self.pubKeyYParHex + cleanHexStr(msgHashHex) + cleanHexStr(nonceTimesGeneratorAddress)

        e = web3.keccak(hexstr=challengeEncodedPacked)
        eInt = int(cleanHexStr(e), 16)

        s = (k - (self.privKeyInt * eInt)) % self.Q_INT
        s = s + self.Q_INT if s < 0 else s

        # Since nonces is passed by reference, it will be altered for all other signers too
        sigData = [int(msgHashHex, 16), s, self.nonces[keyID], nonceTimesGeneratorAddress]

        print(sigData)

        self.nonces[keyID] += 1
        return sigData


    def getSigDataWithNonces(self, msgToHash, nonces, keyID):
        msgHashHex = cleanHexStr(web3.keccak(hexstr=msgToHash))

        # Pick a "random" nonce (k)
        k = int(web3.keccak(hexstr=msgHashHex).hex(), 16)
        kTimesG = tuple(secp256k1.multiply(secp256k1.G, k))

        kTimesGXInt = kTimesG[0] # bigint
        kTimesGYParityInt = kTimesG[1] # bigint
        kTimesGXBytes = (kTimesGXInt).to_bytes(32, byteorder='big')
        kTimesGYParityBytes = (kTimesGYParityInt).to_bytes(32, byteorder='big')
        kTimesGConcat = kTimesGXBytes + kTimesGYParityBytes

        k256 = web3.keccak(kTimesGConcat)
        nonceTimesGeneratorAddress = web3.toChecksumAddress(cleanHexStr(k256)[-40:])
        challengeEncodedPacked = cleanHexStrPad(self.pubKeyX) + self.pubKeyYParHex + cleanHexStr(msgHashHex) + cleanHexStr(nonceTimesGeneratorAddress)

        e = web3.keccak(hexstr=challengeEncodedPacked)
        eInt = int(cleanHexStr(e), 16)

        s = (k - (self.privKeyInt * eInt)) % self.Q_INT
        s = s + self.Q_INT if s < 0 else s

        # Since nonces is passed by reference, it will be altered for all other signers too
        sigData = [int(msgHashHex, 16), s, nonces[keyID], nonceTimesGeneratorAddress]
        nonces[keyID] += 1
        return sigData