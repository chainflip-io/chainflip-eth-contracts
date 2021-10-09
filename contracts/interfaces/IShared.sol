pragma solidity ^0.8.7;


/**
* @title    Shared interface
* @notice   Holds structs needed by other interfaces
* @author   Quantaf1re (James Key)
*/
interface IShared {

    /**
    * @dev  This is used to ensure that isUpdatedValidSig can only accept the agg key
    *       or gov key as opposed to any key, which would otherwise allow
    *       anyone to call isUpdatedValidSig without reverting and therefore change
    *       _lastValidateTime without authorisation
    */
    enum KeyID {
        Agg,
        Gov
    }

    /**
    * @dev  SchnorrSECP256K1 requires that each key has a public key part (x coordinate),
    *       a parity for the y coordinate (0 if the y ordinate of the public key is even, 1
    *       if it's odd)
    */
    struct Key {
        uint pubKeyX;
        uint8 pubKeyYParity;
    }

    /**
    * @dev  Contains a signature and the msgHash that the signature is over. Kept as a single
    *       struct since they should always be used together
    */
    struct SigData {
        uint msgHash;
        uint sig;
        uint nonce;
        address kTimesGAddr;
    }
}