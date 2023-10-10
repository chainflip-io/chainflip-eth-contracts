pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract MultiSend {
    struct TransferParams {
        address recipientAddress;
        uint256 amount;
    }

    address private owner;

    constructor() {
        owner = msg.sender;
    }

    function multiSendToken(IERC20 token, TransferParams[] calldata transferParamsArray, uint256 totalAmount) external {
        require(msg.sender == owner, "Not owner");

        uint256 initialBalance = token.balanceOf(address(this));

        require(token.transferFrom(msg.sender, address(this), totalAmount));

        uint256 length = transferParamsArray.length;
        for (uint256 i = 0; i < length; ) {
            require(token.transfer(transferParamsArray[i].recipientAddress, transferParamsArray[i].amount));
            unchecked {
                ++i;
            }
        }

        // Assumed that this contract won't be in the recipientAddress
        require(token.balanceOf(address(this)) == initialBalance, "MultiSend: TotalAmount != amountSent");
    }

    function recoverTokens(IERC20 token) external {
        require(msg.sender == owner, "Not owner");
        require(token.transfer(msg.sender, token.balanceOf(address(this))));
    }
}
