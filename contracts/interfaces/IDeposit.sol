// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

/*****************************************************************************************************
*********************************        ATTENTION!        *******************************************
******************************************************************************************************
    Modifying this contract won't take effect on the deployed contracts as this contract's bytecode is 
    been hardcoded into the Vault contract. That is done because compiling with different environments 
    might result in different bytecodes and we need to ensure that the bytecode is consistent.
    Do NOT modify unless the consequences of doing so are fully understood. If modifications are done
    don't forget to update the Vault's DEPOSIT_BYTECODE_PRECOMPILED constant.
****************************************************************************************************/

/**
 * @title    Deposit interface
 */
interface IDeposit {
    function fetch(address token) external;

    receive() external payable;
}
