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
        # print(kHex, self.pubKeyXHex)
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

        # Pick a "random" nonce and then hash it just for a laugh
        print(web3.keccak(self.Q_INT % (self.nonces[keyID] + 2)).hex())
        k = int(web3.keccak(self.Q_INT % (self.nonces[keyID] + 2)).hex(), 16)
        kTimesG = tuple(secp256k1.multiply(secp256k1.G, k))

        # Get the x and y ordinate of our K*g value
        kTimesGXHex = hex(kTimesG[0])
        kTimesGYParityHex = hex(kTimesG[1])
        k256 = web3.keccak(hexstr=cleanHexStr(kTimesGXHex) + cleanHexStr(kTimesGYParityHex))
        nonceTimesGeneratorAddress = web3.toChecksumAddress(cleanHexStr(k256)[-40:])
        challengeEncodedPacked = cleanHexStrPad(self.pubKeyX) + self.pubKeyYParHex + cleanHexStr(msgHashHex) + cleanHexStr(nonceTimesGeneratorAddress)

        print("challenge", challengeEncodedPacked)

        # 31b2ba4b46201610901c5164f42edd1f64ce88076fde2e2c544f9dc3d7b350ae
        # 01
        # 2bdc19071c7994f088103dbf8d5476d6deb6d55ee005a2f510dc7640055cc84e
        # 3Eea25034397B249a3eD8614BB4d0533e5b03594

        e = web3.keccak(hexstr=challengeEncodedPacked)
        eInt = int(cleanHexStr(e), 16)

        s = (k - (self.privKeyInt * eInt)) % self.Q_INT
        s = s + self.Q_INT if s < 0 else s

        # Since nonces is passed by reference, it will be altered for all other signers too
        sigData = [int(msgHashHex, 16), s, self.nonces[keyID], nonceTimesGeneratorAddress]

        print(msgHashHex, hex(s), nonceTimesGeneratorAddress)

        self.nonces[keyID] += 1
        return sigData


    def getSigDataWithNonces(self, msgToHash, nonces, keyID):
        msgHashHex = cleanHexStr(web3.keccak(hexstr=msgToHash))

        # Pick a "random" nonce and then hash it just for a laugh
        k = int(web3.keccak(self.Q_INT % (self.nonces[keyID] + 2)).hex(), 16)
        kTimesG = tuple(secp256k1.multiply(secp256k1.G, k))

        # Get the x and y ordinate of our K*g value
        kTimesGXHex = hex(kTimesG[0])
        kTimesGYParityHex = hex(kTimesG[1])
        k256 = web3.keccak(hexstr=cleanHexStr(kTimesGXHex) + cleanHexStr(kTimesGYParityHex))
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