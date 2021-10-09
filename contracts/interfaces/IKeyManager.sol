pragma solidity ^0.8.7;


import "./IShared.sol";


/**
* @title    KeyManager interface
* @notice   The interface for functions KeyManager implements
* @author   Quantaf1re (James Key)
*/
interface IKeyManager is IShared {

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function isUpdatedValidSig(
        SigData memory sigData,
        bytes32 contractMsgHash,
        KeyID keyID
    ) external returns (bool);

    function setAggKeyWithAggKey(
        SigData memory sigData,
        Key memory newKey
    ) external;

    function setAggKeyWithGovKey(
        SigData memory sigData,
        Key memory newKey
    ) external;

    function setGovKeyWithGovKey(
        SigData memory sigData,
        Key memory newKey
    ) external;


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getAggregateKey() external view returns (Key memory);

    function getGovernanceKey() external view returns (Key memory);

    function getLastValidateTime() external view returns (uint);

    function isNonceUsedByKey(KeyID keyID, uint nonce) external view returns (bool);
}