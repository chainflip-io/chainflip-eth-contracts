// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IScUtils {
    function depositToScGateway(uint256 amount, bytes calldata scCall) external;

    function depositToVault(uint256 amount, address token, bytes calldata scCall) external payable;

    function depositTo(uint256 amount, address token, address to, bytes calldata scCall) external payable;

    function callSc(bytes calldata scCall) external;

    function cfReceive(uint32, bytes calldata, bytes calldata message, address token, uint256 amount) external payable;
}
