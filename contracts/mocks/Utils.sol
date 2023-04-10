pragma solidity ^0.8.0;

// import "../StakeManager.sol";
import "../interfaces/IStakeManager.sol";

import "../interfaces/IShared.sol";

contract Utils {
    // Decode the lowLevelData (reason) returned from a failed transaction from a try/catch statement.
    // A check might need to be added in the assembly for returnData.length>0 but we don't really
    // as this is not for production.
    function decodeRevertData(bytes memory returnData) public pure returns (string memory) {
        // If the length is less than 68, then the transaction failed silently (without a revert message)
        if (returnData.length < 68) return "Transaction reverted silently";

        // solhint-disable-next-line no-inline-assembly
        assembly {
            // Slice the sighash.
            returnData := add(returnData, 0x04)
        }
        return abi.decode(returnData, (string)); // All that remains is the revert string
    }

    // This is a workaround for abi.encode that should be done via web3py
    function registerClaimEncode(
        IStakeManager.SigData calldata sigData,
        bytes32 nodeID,
        uint256 amount,
        address staker,
        uint48 expiryTime
    ) public pure returns (bytes32) {
        return
            registerClaimEncode_aux(
                abi.encode(
                    IStakeManager.registerClaim.selector,
                    sigData.keyManAddr,
                    sigData.chainID,
                    0,
                    0,
                    sigData.nonce,
                    address(0),
                    nodeID,
                    amount,
                    staker,
                    expiryTime
                ),
                sigData.nonceConsumerAddr
            );
    }

    function registerClaimEncode_aux(bytes memory data, address nonceConsumerAddr) private pure returns (bytes32) {
        return keccak256(abi.encode(data, nonceConsumerAddr));
    }
}
