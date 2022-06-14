pragma solidity ^0.8.0;

import "../interfaces/IShared.sol";
import "../interfaces/IFLIP.sol";

contract FLIPEchidna is IShared {
    IFLIP public f;

    // Expose FLIP functions to Echidna

    function updateFlipSupply(
        SigData calldata sigData,
        uint256 newTotalSupply,
        uint256 stateChainBlockNumber,
        address staker
    ) external {
        f.updateFlipSupply(sigData, newTotalSupply, stateChainBlockNumber, staker);
    }
}
