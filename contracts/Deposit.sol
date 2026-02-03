// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./interfaces/IERC20Lite.sol";

/**
 * @title    Deposit contract
 * @notice   Creates a contract with a known address and withdraws tokens from it.
 *           After deployment, the Vault will call fetch() to withdraw tokens.
 * @dev      Any change in this contract, including comments, will affect the final
 *           bytecode and therefore will affect the create2 derived addresses.
 *           Do NOT modify unless the consequences of doing so are fully understood.
 */
contract Deposit {
    address payable private immutable vault;

    /**
     * @notice  Upon deployment it fetches the assets (native or ERC20) to the Vault.
     * @param token  The address of the token to fetch
     */
    constructor(address token) {
        vault = payable(msg.sender);
        _fetchAsset(token);
    }

    /**
     * @notice  Allows the Vault to fetch assets (native or ERC20) from this contract.
     * @param token  The address of the token to fetch
     */
    function fetch(address token) external {
        require(msg.sender == vault);
        _fetchAsset(token);
    }

    function _fetchAsset(address token) internal {
        if (token == 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE) {
            uint256 balance = address(this).balance;
            if (balance > 0) {
                // solhint-disable-next-line avoid-low-level-calls
                (bool success, ) = msg.sender.call{value: address(this).balance}("");
                require(success);
            }
        } else {
            uint256 tokenBalance = IERC20Lite(token).balanceOf(address(this));
            if (tokenBalance > 0) {
                // IERC20Lite.transfer doesn't have a return bool to avoid reverts on non-standard ERC20s
                IERC20Lite(token).transfer(msg.sender, IERC20Lite(token).balanceOf(address(this)));
            }
        }
    }

    /// @dev For receiving native asset. Accepts clean transfers.
    receive() external payable {}

    /// @dev Accept TRX with calldata as we can ingress it too
    fallback() external payable {}
}
