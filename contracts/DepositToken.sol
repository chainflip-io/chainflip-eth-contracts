pragma solidity ^0.7.0;


interface IERC20Lite {
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address holder) external view returns (uint);
}

contract DepositToken {

    constructor(address tokenAddr) {
        IERC20Lite(tokenAddr).transfer(
            msg.sender,
            IERC20Lite(tokenAddr).balanceOf(address(this))
        );
        // If there's any ETH here by mistake, send it back to the vault.
        selfdestruct(msg.sender);
    }

}