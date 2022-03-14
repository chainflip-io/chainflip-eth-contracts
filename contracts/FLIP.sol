pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./interfaces/IFLIP.sol";
import "./abstract/Shared.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title    FLIP contract
 * @notice   The FLIP utility token which is used to stake in the FLIP system and pay for
 *           trap fees with
 * @author   Quantaf1re (James Key)
 */
contract FLIP is ERC20, ERC20Burnable, Ownable, Shared {
    using Counters for Counters.Counter;

    mapping(address => Counters.Counter) private _nonces;

    string public constant VERSION = "1";

    // solhint-disable-next-line var-name-mixedcase
    bytes32 private immutable DOMAIN_SEPARATOR;

    bytes32 private constant _PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");

    constructor(
        string memory name,
        string memory symbol,
        address receiver,
        uint256 mintAmount,
        uint256 chainId_
    ) ERC20(name, symbol) Ownable() nzAddr(receiver) nzUint(mintAmount) {
        DOMAIN_SEPARATOR = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes(name)),
                keccak256(bytes(VERSION)),
                chainId_,
                address(this)
            )
        );
        _mint(receiver, mintAmount);
    }

    function mint(address receiver, uint256 amount) external nzAddr(receiver) nzUint(amount) onlyOwner {
        _mint(receiver, amount);
    }

    /**
     * @notice  ERC20 Permit function
     *          Using value input instead of nonce to control the amount of FLIP
     */
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) public {
        // Do we want indefinite time permission option?
        require(deadline == 0 || block.timestamp <= deadline, "ERC20Permit: expired deadline");

        bytes32 digest = keccak256(
            abi.encodePacked(
                "\x19\x01",
                DOMAIN_SEPARATOR,
                keccak256(abi.encode(_PERMIT_TYPEHASH, owner, spender, value, _useNonce(owner), deadline))
            )
        );

        require(owner != address(0), "FLIP/invalid-address-0");
        require(owner == ecrecover(digest, v, r, s), "FLIP/invalid-permit");

        _approve(owner, spender, value);
    }

    /**
     * @dev See {IERC20Permit-nonces}.
     */
    function nonces(address owner) public view returns (uint256) {
        return _nonces[owner].current();
    }

    /**
     * @dev See {IERC20Permit-DOMAIN_SEPARATOR}.
     */
    // solhint-disable-next-line func-name-mixedcase
    function domain_separator() external view returns (bytes32) {
        return DOMAIN_SEPARATOR;
    }

    /**
     * @dev "Consume a nonce": return the current value and increment.
     */
    function _useNonce(address owner) internal returns (uint256 current) {
        Counters.Counter storage nonce = _nonces[owner];
        current = nonce.current();
        nonce.increment();
    }
}
