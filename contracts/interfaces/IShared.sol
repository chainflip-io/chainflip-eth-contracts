pragma solidity ^0.8.0;

/**
 * @title    Shared interface
 * @notice   Holds structs needed by other interfaces
 */
interface IShared {
    /**
     * @dev  SchnorrSECP256K1 requires that each key has a public key part (x coordinate),
     *       a parity for the y coordinate (0 if the y ordinate of the public key is even, 1
     *       if it's odd)
     */
    struct Key {
        uint256 pubKeyX;
        uint8 pubKeyYParity;
    }

    /**
     * @dev  Contains a signature and the msgHash that the signature is over. Kept as a single
     *       struct since they should always be used together
     */
    struct SigData {
        address keyManAddr;
        uint256 chainID;
        uint256 msgHash;
        uint256 sig;
        uint256 nonce;
        address kTimesGAddress;
    }
}
