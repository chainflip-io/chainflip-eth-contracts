pragma solidity ^0.8.0;

import "./IShared.sol";

/**
 * @title    KeyManager interface
 * @notice   The interface for functions KeyManager implements
 * @author   Quantaf1re (James Key)
 */
interface IKeyManager is IShared {
    event AggKeySetByAggKey(Key oldKey, Key newKey);
    event AggKeySetByGovKey(Key oldKey, Key newKey);
    event GovKeySetByGovKey(address oldKey, address newKey);
    event SignatureAccepted(SigData sigData, address broadcaster);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function consumeKeyNonce(SigData memory sigData, bytes32 contractMsgHash) external returns (bool);

    function setAggKeyWithAggKey(SigData memory sigData, Key memory newKey) external;

    function setAggKeyWithGovKey(Key memory newKey) external;

    function setGovKeyWithGovKey(address newKey) external;

    function canConsumeNonce(address addr) external view returns (bool);

    function canConsumeNonceSet() external view returns (bool);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getAggregateKey() external view returns (Key memory);

    function getGovernanceKey() external view returns (address);

    function getLastValidateTime() external view returns (uint256);

    function getNumberWhitelistedAddresses() external view returns (uint256);

    function isNonceUsedByAggKey(uint256 nonce) external view returns (bool);
}
