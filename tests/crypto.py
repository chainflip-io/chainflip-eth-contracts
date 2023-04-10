from utils import *
from brownie import chain
import umbral
from umbral import SecretKey
from py_ecc.secp256k1 import secp256k1

# Fcns return a list instead of a tuple since they need to be modified
# for some tests (e.g. to make them revert)
class Signer:

    Q = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141"
    Q_INT = int(Q, 16)
    HALF_Q_INT = (Q_INT >> 1) + 1
    AGG = "Agg"

    def __init__(self, privKeyHex, keyID, nonces):
        self.privKeyHex = privKeyHex
        self.privKey = SecretKey._from_exact_bytes(bytes.fromhex(privKeyHex))
        self.privKeyInt = int(self.privKeyHex, 16)

        self.pubKey = self.privKey.public_key()
        self.pubKeyX = bytes(self.pubKey)[1:]
        self.pubKeyXHex = cleanHexStr(self.pubKeyX)
        self.pubKeyXInt = int(self.pubKeyXHex, 16)

        self.pubKeyYPar = 0 if cleanHexStr(bytes(self.pubKey)[:1]) == "02" else 1
        self.pubKeyYParHex = "00" if self.pubKeyYPar == 0 else "01"

        self.nonces = nonces

    @classmethod
    def priv_key_to_pubX_int(cls, privKey):
        pubKey = privKey.public_key()
        pubKeyX = bytes(pubKey)[1:]
        return int(cleanHexStr(pubKeyX), 16)

    @classmethod
    def gen_key(cls):
        key = SecretKey.random()
        while cls.priv_key_to_pubX_int(key) >= cls.HALF_Q_INT:
            key = SecretKey.random()

        return key

    @classmethod
    def gen_key_hex(cls):
        return cls.gen_key().to_secret_bytes().hex()

    @classmethod
    def gen_signer(cls, keyID, nonces):
        privKeyHex = cls.gen_key_hex()
        return cls(privKeyHex, keyID, nonces)

    def getPubData(self):
        return [self.pubKeyXInt, self.pubKeyYPar]

    def getPubDataWith0x(self):
        return [self.pubKeyXInt, self.pubKeyYPar]

    def getSigData(self, msgToHash, keyManagerAddress, nonceConsumerAddress):
        return self.getSigDataWithNonces(
            msgToHash, self.nonces, keyManagerAddress, nonceConsumerAddress
        )

    def getSigDataWithNonces(
        self, msgToHash, nonces, keyManagerAddress, nonceConsumerAddress
    ):

        # Encode the data
        # msgHashHex = cleanHexStr(web3.keccak(hexstr=msgToHash))
        msgHashHex = msgToHash

        # Mimic abi.encode with padding. It could technically be packed
        # but it's not like we are saving much gas.
        msgToHash = msgHashHex + cleanHexStrPad(nonceConsumerAddress)
        msgHashHex = cleanHexStr(web3.keccak(hexstr=msgToHash))

        [s, nonceTimesGeneratorAddress] = self.sign(msgHashHex)
        sigData = [
            keyManagerAddress,
            chain.id,
            int(msgHashHex, 16),
            s,
            nonces[self.AGG],
            nonceTimesGeneratorAddress,
            nonceConsumerAddress,
        ]

        # Since nonces is passed by reference, it will be altered for all other signers too
        nonces[self.AGG] += 1
        return sigData

    # @dev reference /contracts/abstract/SchnorrSECP256k1.sol
    def sign(self, msgHashHex):
        # Pick a "random" nonce (k)
        k = int(web3.keccak(hexstr=msgHashHex).hex(), 16)
        kTimesG = tuple(secp256k1.multiply(secp256k1.G, k))

        # Get the x and y ordinate of our k*G value
        kTimesGXInt = kTimesG[0]
        kTimesGYInt = kTimesG[1]
        kTimesGXBytes = (kTimesGXInt).to_bytes(32, byteorder="big")
        kTimesGYParityBytes = (kTimesGYInt).to_bytes(32, byteorder="big")
        kTimesGConcat = kTimesGXBytes + kTimesGYParityBytes

        # Get the hash of the concatenated (uncompressed) key
        k256 = web3.keccak(kTimesGConcat)

        # Get the last 20 bytes of the hash, which is Ethereum Address format
        nonceTimesGeneratorAddress = web3.toChecksumAddress(cleanHexStr(k256)[-40:])

        challengeEncodedPacked = (
            cleanHexStrPad(self.pubKeyX)
            + self.pubKeyYParHex
            + cleanHexStr(msgHashHex)
            + cleanHexStr(nonceTimesGeneratorAddress)
        )

        e = web3.keccak(hexstr=challengeEncodedPacked)
        eInt = int(cleanHexStr(e), 16)

        s = (k - (self.privKeyInt * eInt)) % self.Q_INT
        s = s + self.Q_INT if s < 0 else s

        return [s, nonceTimesGeneratorAddress]
