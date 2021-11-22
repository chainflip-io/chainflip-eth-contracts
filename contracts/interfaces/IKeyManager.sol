pragma solidity ^0.8.0;


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
        bytes32 contractMsgHash
    ) external returns (bool);

    function setAggKeyWithAggKey(
        SigData memory sigData,
        Key memory newKey
    ) external;

    function setAggKeyWithGovKey(
        Key memory newKey
    ) external;

    function setGovKeyWithGovKey(
        address newKey
    ) external;

    function canValidateSig(address addr) external view returns (bool);

    function canValidateSigSet() external view returns (bool);


    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getAggregateKey() external view returns (Key memory);

    function getGovernanceKey() external view returns (address);

    function getLastValidateTime() external view returns (uint);

    function isNonceUsedByAggKey(uint nonce) external view returns (bool);
}