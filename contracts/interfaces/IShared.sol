pragma solidity ^0.7.0;


/**
* @title    Shared interface
* @notice   Holds structs needed by other interfaces
* @author   Quantaf1re (James Key)
*/
interface IShared {

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
