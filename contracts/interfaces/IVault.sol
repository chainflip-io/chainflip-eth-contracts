pragma solidity ^0.7.0;


interface IVault {

    // -----Deposits/withdrawals-----

    function transfer(
        uint msgHash,
        uint sig,
        address tokenAddr,
        address payable recipient,
        uint amount
    ) external;

    function fetchDeposit(
        uint msgHash,
        uint sig,
        bytes32 swapID,
        address tokenAddr,
        uint amount
    ) external;


    // -----Setters-----

    function setAggKeyByAggKey(
        uint msgHash,
        uint sig,
        uint newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr
    ) external;

    function setAggKeyByGovKey(
        uint msgHash,
        uint sig,
        uint newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr
    ) external;

    function setGovKeyByGovKey(
        uint msgHash,
        uint sig,
        uint newKeyX,
        uint8 newKeyYParity,
        address newNonceTimesGAddr
    ) external;


    // -----Getters-----

    function getAggregateKeyData() external view returns (uint, uint8, address);

    function getGovernanceKeyData() external view returns (uint, uint8, address);

    function getLastValidateTime() external view returns (uint);
}