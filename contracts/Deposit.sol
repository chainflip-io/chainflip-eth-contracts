pragma solidity ^0.8.0;

import "./interfaces/IERC20Lite.sol";

/**
 * @title    DepositToken contract
 * @notice   Creates a contract with a known address and withdraws tokens from it.
 *           After deployment, the Vault will call fetch() to withdraw tokens.
 * @dev      The logic is not refactored into a single function because it's cheaper.
 */
contract Deposit {
    address payable private vault;

    constructor(IERC20Lite token) {
        vault = payable(msg.sender);
        if (address(token) == 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE) {
            payable(msg.sender).transfer(address(this).balance);
        } else {
            require(token.transfer(msg.sender, token.balanceOf(address(this))));
        }
    }

    function fetch(IERC20Lite token) external {
        require(msg.sender == vault);
        // Slightly cheaper to use msg.sender instead of Vault. To use Vault if we
        // end up removing the check above.
        if (address(token) == 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE) {
            payable(msg.sender).transfer(address(this).balance);
        } else {
            require(token.transfer(msg.sender, token.balanceOf(address(this))));
        }
    }

    receive() external payable {}
}
