pragma solidity ^0.8.0;

import "../CFReceiver.sol";
import "../abstract/Shared.sol";
import "../interfaces/IVault.sol";

/**
 * @title    LoopBackMock
 * @dev      Mock of a loopback
 */
contract LoopBackMock is CFReceiver, Shared {
    constructor(address cfSender) CFReceiver(cfSender) nzAddr(cfSender) {}

    function _cfRecieve(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        // ingressParams == ingressChain
        // In solidity 8.12 string.concat() can be used. It is slightly cheaper.
        // TODO: Maybe ingressParams here should be chain+ingressToken? And only chain in _cfRecieveOnlyxCall?
        string memory egressParams = string(abi.encodePacked(ingressParams, ":", "USDC"));
        if (token == _ETH_ADDR) {
            // Just health check for this mock. It will never revert.
            require(msg.value == amount, "LoopbackMock: msg.value != amount");
            IVault(_cfSender).xSwapNativeWithCall{value: amount}(egressParams, ingressAddress, message, address(this));
        } else {
            IERC20(token).approve(msg.sender, amount);
            IVault(_cfSender).xswapTokenWithCall(
                egressParams,
                ingressAddress,
                message,
                IERC20(token),
                amount,
                address(this)
            );
        }
    }

    function _cfRecieveOnlyxCall(
        string calldata ingressParams,
        string calldata ingressAddress,
        bytes calldata message
    ) internal override {
        // ingressParams == ingressChain
        IVault(_cfSender).xSwapNativeWithCall{value: 200000 * 12}(
            ingressParams,
            ingressAddress,
            message,
            address(this)
        );
    }

    // Just leaving this here as a proof of concept of slicing strings. We could make all chainNames to be
    // 3 char long so the user can know where to split the string if they need to.
    function getSlice(uint256 begin, uint256 end, string memory text) public pure returns (string memory) {
        bytes memory a = new bytes(end-begin+1);
        for(uint i=0;i<=end-begin;i++){
            a[i] = bytes(text)[i+begin-1];
        }
        return string(a);    
    }
}
