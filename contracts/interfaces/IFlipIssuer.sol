// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "./IFLIP.sol";

/**
 * @title    Flip Issuer interface
 * @notice   This interface is required when updating the FLIP issuer.
 *           Additionally, any contract inheriting this should implement the
 *           mint and burn capabilities to interact with the FLIP contract.
 */
interface IFlipIssuer {
    /**
     * @notice  Get the FLIP token address
     * @return  The address of FLIP
     */
    function getFLIP() external view returns (IFLIP);
}
