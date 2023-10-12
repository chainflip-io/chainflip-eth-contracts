// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

interface IAirdrop {
    /**
     *
     * @param _recipients list of recipients
     * @param _amounts  list of amounts to send each recipient
     */
    function airdropETH(address[] calldata _recipients, uint256[] calldata _amounts) external;

    /**
     *
     * @param _token ERC20 token to airdrop
     * @param _recipients list of recipients
     * @param _amounts list of amounts to send each recipient
     * @param _total total amount to transfer from caller
     */
    function airdropERC20(
        address _token,
        address[] calldata _recipients,
        uint256[] calldata _amounts,
        uint256 _total
    ) external;
}
