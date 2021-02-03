pragma solidity ^0.7.0;


/**
* @title    Shared interface
* @notice   Holds structs needed by other interfaces
* @author   Quantaf1re (James Key)
*/
interface IShared {

    /**
    * @dev  This is used to ensure that isValidSig can only accept the agg key
    *       or gov key as opposed to any key, which would otherwise allow
    *       anyone to call isValidSig without reverting and therefore change
    *       _lastValidateTime without authorisation
    */
    enum KeyID {
        Agg,
        Gov
    }

    struct Key {
        uint pubKeyX;
        uint8 pubKeyYParity;
        address nonceTimesGAddr;
    }

    struct SigData {
        uint msgHash;
        uint sig;
    }
}
