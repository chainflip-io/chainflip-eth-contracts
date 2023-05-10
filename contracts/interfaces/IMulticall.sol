pragma solidity ^0.8.17;

interface IMulticall {
    enum CallType {
        Default,
        FullTokenBalance,
        FullNativeBalance,
        CollectTokenBalance
    }

    struct Call {
        CallType callType;
        address target;
        uint256 value;
        bytes callData;
        bytes payload;
    }

    error AlreadyRunning();
    error CallFailed(uint256 callPosition, bytes reason);

    function run(Call[] calldata calls, address token, uint256 amount) external payable;
}
