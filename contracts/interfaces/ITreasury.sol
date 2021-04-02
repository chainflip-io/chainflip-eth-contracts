pragma solidity ^0.8.0;


import "@openzeppelin/contracts/token/ERC20/IERC20.sol";


interface ITreasury {

    /**
     * @notice  Checks the Treasury's balance of all supported assets and
     *          lends them out if they're non-zero. Updates the record
     *          of how much of each asset is currently lent out (not including
     *          the interest/yield)
     */
    function lend() external;

    /**
     * @notice  Withdraw a specific amount from lending platforms and send it to the Vault.
     *          Since this Vault shouldn't have any knowledge of what lending platforms
     *          etc are used, it should trust the Treasury to calculate how much needs
     *          to be withdrawn from whatever platform such that the initially lent
     *          amount + interest equals amount.
     * @param asset The address of the asset to withdraw
     * @param amount    The amount to send to the Vault. The amount withdrawn from the
     *                  actual lending platforms will be less as the Treasury accounts
     *                  for interest/yield received after withdrawing
     */
    function withdraw(IERC20 asset, uint amount) external;

    /**
     * @notice  Gets the amount of an asset that's been lent out in total over
     *          various platforms incl yield. The Vault needs to know this so that it can
     *          calculate whether its own balance is within its own 'hot wallet'
     *          bounds and therefore withdraw some if it's low or send & lend if
     *          it has too much
     * @return  The amount of that asset that's been lent out (uint)
     */
    function getLentAmount(IERC20 asset) external returns (uint);
}