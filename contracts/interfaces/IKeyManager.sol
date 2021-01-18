pragma solidity ^0.7.0;
pragma abicoder v2;


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

    function isValidSig(
        bytes32 contractMsgHash,
        SigData memory sigData,
        Key memory key
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
}