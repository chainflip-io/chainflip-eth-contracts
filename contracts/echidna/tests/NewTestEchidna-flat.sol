pragma solidity 0.8.20;
IHevm constant hevm = IHevm(0x7109709ECfa91a80626fF3989D68f67F5b1DD12D);

function bytesToString(bytes memory data) pure returns (string memory) {
    uint256 len = 2 * data.length;
    bytes memory out = new bytes(len);
    bytes memory hexdigits = "0123456789abcdef";

    for (uint i = 0; i < data.length; i++) {
        out[i * 2] = hexdigits[uint(uint8(data[i]) >> 4)];
        out[i * 2 + 1] = hexdigits[uint(uint8(data[i]) & 0x0f)];
    }
    return string(out);
}

function toString(uint256 value) pure returns (string memory str) {
    /// @solidity memory-safe-assembly
    assembly {
        // The maximum value of a uint256 contains 78 digits (1 byte per digit), but we allocate 160 bytes
        // to keep the free memory pointer word aligned. We'll need 1 word for the length, 1 word for the
        // trailing zeros padding, and 3 other words for a max of 78 digits. In total: 5 * 32 = 160 bytes.
        let newFreeMemoryPointer := add(mload(0x40), 160)

        // Update the free memory pointer to avoid overriding our string.
        mstore(0x40, newFreeMemoryPointer)

        // Assign str to the end of the zone of newly allocated memory.
        str := sub(newFreeMemoryPointer, 32)

        // Clean the last word of memory it may not be overwritten.
        mstore(str, 0)

        // Cache the end of the memory to calculate the length later.
        let end := str

        // We write the string from rightmost digit to leftmost digit.
        // The following is essentially a do-while loop that also handles the zero case.
        // prettier-ignore
        for { let temp := value } 1 {} {
            // Move the pointer 1 byte to the left.
            str := sub(str, 1)

            // Write the character to the pointer.
            // The ASCII index of the '0' character is 48.
            mstore8(str, add(48, mod(temp, 10)))

            // Keep dividing temp until zero.
            temp := div(temp, 10)

                // prettier-ignore
            if iszero(temp) { break }
        }

        // Compute and cache the final total length of the string.
        let length := sub(end, str)

        // Move the pointer 32 bytes leftwards to make room for the length.
        str := sub(str, 32)

        // Store the string's length at the start of memory allocated for our string.
        mstore(str, length)
    }
}

interface IShared {
    /**
     * @dev  SchnorrSECP256K1 requires that each key has a public key part (x coordinate),
     *       a parity for the y coordinate (0 if the y ordinate of the public key is even, 1
     *       if it's odd)
     */
    struct Key {
        uint256 pubKeyX;
        uint8 pubKeyYParity;
    }

    /**
     * @dev  Contains a signature and the nonce used to create it. Also the recovered address
     *       to check that the signature is valid
     */
    struct SigData {
        uint256 sig;
        uint256 nonce;
        address kTimesGAddress;
    }

    /**
     * @param token The address of the token to be transferred
     * @param recipient The address of the recipient of the transfer
     * @param amount    The amount to transfer, in wei (uint)
     */
    struct TransferParams {
        address token;
        address payable recipient;
        uint256 amount;
    }

    /**
     * @param swapID    The unique identifier for this swap (bytes32), used for create2
     * @param token     The token to be transferred
     */
    struct DeployFetchParams {
        bytes32 swapID;
        address token;
    }

    /**
     * @param fetchContract   The address of the deployed Deposit contract
     * @param token     The token to be transferred
     */
    struct FetchParams {
        address payable fetchContract;
        address token;
    }
}

abstract contract Context {
    function _msgSender() internal view virtual returns (address) {
        return msg.sender;
    }

    function _msgData() internal view virtual returns (bytes calldata) {
        return msg.data;
    }
}

abstract contract Ownable is Context {
    address private _owner;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    /**
     * @dev Initializes the contract setting the deployer as the initial owner.
     */
    constructor() {
        _transferOwnership(_msgSender());
    }

    /**
     * @dev Throws if called by any account other than the owner.
     */
    modifier onlyOwner() {
        _checkOwner();
        _;
    }

    /**
     * @dev Returns the address of the current owner.
     */
    function owner() public view virtual returns (address) {
        return _owner;
    }

    /**
     * @dev Throws if the sender is not the owner.
     */
    function _checkOwner() internal view virtual {
        require(owner() == _msgSender(), "Ownable: caller is not the owner");
    }

    /**
     * @dev Leaves the contract without owner. It will not be possible to call
     * `onlyOwner` functions anymore. Can only be called by the current owner.
     *
     * NOTE: Renouncing ownership will leave the contract without an owner,
     * thereby removing any functionality that is only available to the owner.
     */
    function renounceOwnership() public virtual onlyOwner {
        _transferOwnership(address(0));
    }

    /**
     * @dev Transfers ownership of the contract to a new account (`newOwner`).
     * Can only be called by the current owner.
     */
    function transferOwnership(address newOwner) public virtual onlyOwner {
        require(newOwner != address(0), "Ownable: new owner is the zero address");
        _transferOwnership(newOwner);
    }

    /**
     * @dev Transfers ownership of the contract to a new account (`newOwner`).
     * Internal function without access restriction.
     */
    function _transferOwnership(address newOwner) internal virtual {
        address oldOwner = _owner;
        _owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
}

interface IERC20 {
    /**
     * @dev Emitted when `value` tokens are moved from one account (`from`) to
     * another (`to`).
     *
     * Note that `value` may be zero.
     */
    event Transfer(address indexed from, address indexed to, uint256 value);

    /**
     * @dev Emitted when the allowance of a `spender` for an `owner` is set by
     * a call to {approve}. `value` is the new allowance.
     */
    event Approval(address indexed owner, address indexed spender, uint256 value);

    /**
     * @dev Returns the amount of tokens in existence.
     */
    function totalSupply() external view returns (uint256);

    /**
     * @dev Returns the amount of tokens owned by `account`.
     */
    function balanceOf(address account) external view returns (uint256);

    /**
     * @dev Moves `amount` tokens from the caller's account to `to`.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transfer(address to, uint256 amount) external returns (bool);

    /**
     * @dev Returns the remaining number of tokens that `spender` will be
     * allowed to spend on behalf of `owner` through {transferFrom}. This is
     * zero by default.
     *
     * This value changes when {approve} or {transferFrom} are called.
     */
    function allowance(address owner, address spender) external view returns (uint256);

    /**
     * @dev Sets `amount` as the allowance of `spender` over the caller's tokens.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * IMPORTANT: Beware that changing an allowance with this method brings the risk
     * that someone may use both the old and the new allowance by unfortunate
     * transaction ordering. One possible solution to mitigate this race
     * condition is to first reduce the spender's allowance to 0 and set the
     * desired value afterwards:
     * https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
     *
     * Emits an {Approval} event.
     */
    function approve(address spender, uint256 amount) external returns (bool);

    /**
     * @dev Moves `amount` tokens from `from` to `to` using the
     * allowance mechanism. `amount` is then deducted from the caller's
     * allowance.
     *
     * Returns a boolean value indicating whether the operation succeeded.
     *
     * Emits a {Transfer} event.
     */
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

interface IERC20Metadata is IERC20 {
    /**
     * @dev Returns the name of the token.
     */
    function name() external view returns (string memory);

    /**
     * @dev Returns the symbol of the token.
     */
    function symbol() external view returns (string memory);

    /**
     * @dev Returns the decimals places of the token.
     */
    function decimals() external view returns (uint8);
}

contract ERC20 is Context, IERC20, IERC20Metadata {
    mapping(address => uint256) private _balances;

    mapping(address => mapping(address => uint256)) private _allowances;

    uint256 private _totalSupply;

    string private _name;
    string private _symbol;

    /**
     * @dev Sets the values for {name} and {symbol}.
     *
     * The default value of {decimals} is 18. To select a different value for
     * {decimals} you should overload it.
     *
     * All two of these values are immutable: they can only be set once during
     * construction.
     */
    constructor(string memory name_, string memory symbol_) {
        _name = name_;
        _symbol = symbol_;
    }

    /**
     * @dev Returns the name of the token.
     */
    function name() public view virtual override returns (string memory) {
        return _name;
    }

    /**
     * @dev Returns the symbol of the token, usually a shorter version of the
     * name.
     */
    function symbol() public view virtual override returns (string memory) {
        return _symbol;
    }

    /**
     * @dev Returns the number of decimals used to get its user representation.
     * For example, if `decimals` equals `2`, a balance of `505` tokens should
     * be displayed to a user as `5.05` (`505 / 10 ** 2`).
     *
     * Tokens usually opt for a value of 18, imitating the relationship between
     * Ether and Wei. This is the value {ERC20} uses, unless this function is
     * overridden;
     *
     * NOTE: This information is only used for _display_ purposes: it in
     * no way affects any of the arithmetic of the contract, including
     * {IERC20-balanceOf} and {IERC20-transfer}.
     */
    function decimals() public view virtual override returns (uint8) {
        return 18;
    }

    /**
     * @dev See {IERC20-totalSupply}.
     */
    function totalSupply() public view virtual override returns (uint256) {
        return _totalSupply;
    }

    /**
     * @dev See {IERC20-balanceOf}.
     */
    function balanceOf(address account) public view virtual override returns (uint256) {
        return _balances[account];
    }

    /**
     * @dev See {IERC20-transfer}.
     *
     * Requirements:
     *
     * - `to` cannot be the zero address.
     * - the caller must have a balance of at least `amount`.
     */
    function transfer(address to, uint256 amount) public virtual override returns (bool) {
        address owner = _msgSender();
        _transfer(owner, to, amount);
        return true;
    }

    /**
     * @dev See {IERC20-allowance}.
     */
    function allowance(address owner, address spender) public view virtual override returns (uint256) {
        return _allowances[owner][spender];
    }

    /**
     * @dev See {IERC20-approve}.
     *
     * NOTE: If `amount` is the maximum `uint256`, the allowance is not updated on
     * `transferFrom`. This is semantically equivalent to an infinite approval.
     *
     * Requirements:
     *
     * - `spender` cannot be the zero address.
     */
    function approve(address spender, uint256 amount) public virtual override returns (bool) {
        address owner = _msgSender();
        _approve(owner, spender, amount);
        return true;
    }

    /**
     * @dev See {IERC20-transferFrom}.
     *
     * Emits an {Approval} event indicating the updated allowance. This is not
     * required by the EIP. See the note at the beginning of {ERC20}.
     *
     * NOTE: Does not update the allowance if the current allowance
     * is the maximum `uint256`.
     *
     * Requirements:
     *
     * - `from` and `to` cannot be the zero address.
     * - `from` must have a balance of at least `amount`.
     * - the caller must have allowance for ``from``'s tokens of at least
     * `amount`.
     */
    function transferFrom(address from, address to, uint256 amount) public virtual override returns (bool) {
        address spender = _msgSender();
        _spendAllowance(from, spender, amount);
        _transfer(from, to, amount);
        return true;
    }

    /**
     * @dev Atomically increases the allowance granted to `spender` by the caller.
     *
     * This is an alternative to {approve} that can be used as a mitigation for
     * problems described in {IERC20-approve}.
     *
     * Emits an {Approval} event indicating the updated allowance.
     *
     * Requirements:
     *
     * - `spender` cannot be the zero address.
     */
    function increaseAllowance(address spender, uint256 addedValue) public virtual returns (bool) {
        address owner = _msgSender();
        _approve(owner, spender, allowance(owner, spender) + addedValue);
        return true;
    }

    /**
     * @dev Atomically decreases the allowance granted to `spender` by the caller.
     *
     * This is an alternative to {approve} that can be used as a mitigation for
     * problems described in {IERC20-approve}.
     *
     * Emits an {Approval} event indicating the updated allowance.
     *
     * Requirements:
     *
     * - `spender` cannot be the zero address.
     * - `spender` must have allowance for the caller of at least
     * `subtractedValue`.
     */
    function decreaseAllowance(address spender, uint256 subtractedValue) public virtual returns (bool) {
        address owner = _msgSender();
        uint256 currentAllowance = allowance(owner, spender);
        require(currentAllowance >= subtractedValue, "ERC20: decreased allowance below zero");
        unchecked {
            _approve(owner, spender, currentAllowance - subtractedValue);
        }

        return true;
    }

    /**
     * @dev Moves `amount` of tokens from `from` to `to`.
     *
     * This internal function is equivalent to {transfer}, and can be used to
     * e.g. implement automatic token fees, slashing mechanisms, etc.
     *
     * Emits a {Transfer} event.
     *
     * Requirements:
     *
     * - `from` cannot be the zero address.
     * - `to` cannot be the zero address.
     * - `from` must have a balance of at least `amount`.
     */
    function _transfer(address from, address to, uint256 amount) internal virtual {
        require(from != address(0), "ERC20: transfer from the zero address");
        require(to != address(0), "ERC20: transfer to the zero address");

        _beforeTokenTransfer(from, to, amount);

        uint256 fromBalance = _balances[from];
        require(fromBalance >= amount, "ERC20: transfer amount exceeds balance");
        unchecked {
            _balances[from] = fromBalance - amount;
            // Overflow not possible: the sum of all balances is capped by totalSupply, and the sum is preserved by
            // decrementing then incrementing.
            _balances[to] += amount;
        }

        emit Transfer(from, to, amount);

        _afterTokenTransfer(from, to, amount);
    }

    /** @dev Creates `amount` tokens and assigns them to `account`, increasing
     * the total supply.
     *
     * Emits a {Transfer} event with `from` set to the zero address.
     *
     * Requirements:
     *
     * - `account` cannot be the zero address.
     */
    function _mint(address account, uint256 amount) internal virtual {
        require(account != address(0), "ERC20: mint to the zero address");

        _beforeTokenTransfer(address(0), account, amount);

        _totalSupply += amount;
        unchecked {
            // Overflow not possible: balance + amount is at most totalSupply + amount, which is checked above.
            _balances[account] += amount;
        }
        emit Transfer(address(0), account, amount);

        _afterTokenTransfer(address(0), account, amount);
    }

    /**
     * @dev Destroys `amount` tokens from `account`, reducing the
     * total supply.
     *
     * Emits a {Transfer} event with `to` set to the zero address.
     *
     * Requirements:
     *
     * - `account` cannot be the zero address.
     * - `account` must have at least `amount` tokens.
     */
    function _burn(address account, uint256 amount) internal virtual {
        require(account != address(0), "ERC20: burn from the zero address");

        _beforeTokenTransfer(account, address(0), amount);

        uint256 accountBalance = _balances[account];
        require(accountBalance >= amount, "ERC20: burn amount exceeds balance");
        unchecked {
            _balances[account] = accountBalance - amount;
            // Overflow not possible: amount <= accountBalance <= totalSupply.
            _totalSupply -= amount;
        }

        emit Transfer(account, address(0), amount);

        _afterTokenTransfer(account, address(0), amount);
    }

    /**
     * @dev Sets `amount` as the allowance of `spender` over the `owner` s tokens.
     *
     * This internal function is equivalent to `approve`, and can be used to
     * e.g. set automatic allowances for certain subsystems, etc.
     *
     * Emits an {Approval} event.
     *
     * Requirements:
     *
     * - `owner` cannot be the zero address.
     * - `spender` cannot be the zero address.
     */
    function _approve(address owner, address spender, uint256 amount) internal virtual {
        require(owner != address(0), "ERC20: approve from the zero address");
        require(spender != address(0), "ERC20: approve to the zero address");

        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }

    /**
     * @dev Updates `owner` s allowance for `spender` based on spent `amount`.
     *
     * Does not update the allowance amount in case of infinite allowance.
     * Revert if not enough allowance is available.
     *
     * Might emit an {Approval} event.
     */
    function _spendAllowance(address owner, address spender, uint256 amount) internal virtual {
        uint256 currentAllowance = allowance(owner, spender);
        if (currentAllowance != type(uint256).max) {
            require(currentAllowance >= amount, "ERC20: insufficient allowance");
            unchecked {
                _approve(owner, spender, currentAllowance - amount);
            }
        }
    }

    /**
     * @dev Hook that is called before any transfer of tokens. This includes
     * minting and burning.
     *
     * Calling conditions:
     *
     * - when `from` and `to` are both non-zero, `amount` of ``from``'s tokens
     * will be transferred to `to`.
     * - when `from` is zero, `amount` tokens will be minted for `to`.
     * - when `to` is zero, `amount` of ``from``'s tokens will be burned.
     * - `from` and `to` are never both zero.
     *
     * To learn more about hooks, head to xref:ROOT:extending-contracts.adoc#using-hooks[Using Hooks].
     */
    function _beforeTokenTransfer(address from, address to, uint256 amount) internal virtual {}

    /**
     * @dev Hook that is called after any transfer of tokens. This includes
     * minting and burning.
     *
     * Calling conditions:
     *
     * - when `from` and `to` are both non-zero, `amount` of ``from``'s tokens
     * has been transferred to `to`.
     * - when `from` is zero, `amount` tokens have been minted for `to`.
     * - when `to` is zero, `amount` of ``from``'s tokens have been burned.
     * - `from` and `to` are never both zero.
     *
     * To learn more about hooks, head to xref:ROOT:extending-contracts.adoc#using-hooks[Using Hooks].
     */
    function _afterTokenTransfer(address from, address to, uint256 amount) internal virtual {}
}

contract MockToken is ERC20, Ownable {
    constructor(string memory _name, string memory _symbol) ERC20(_name, _symbol) {}

    function mint(address to, uint256 amount) public onlyOwner {
        _mint(to, amount);
    }
}

interface IKeyManager is IShared {
    event AggKeySetByAggKey(Key oldAggKey, Key newAggKey);
    event AggKeySetByGovKey(Key oldAggKey, Key newAggKey);
    event GovKeySetByAggKey(address oldGovKey, address newGovKey);
    event GovKeySetByGovKey(address oldGovKey, address newGovKey);
    event CommKeySetByAggKey(address oldCommKey, address newCommKey);
    event CommKeySetByCommKey(address oldCommKey, address newCommKey);
    event SignatureAccepted(SigData sigData, address signer);
    event GovernanceAction(bytes32 message);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function consumeKeyNonce(SigData memory sigData, bytes32 contractMsgHash) external;

    function setAggKeyWithAggKey(SigData memory sigData, Key memory newAggKey) external;

    function setAggKeyWithGovKey(Key memory newAggKey) external;

    function setGovKeyWithAggKey(SigData calldata sigData, address newGovKey) external;

    function setGovKeyWithGovKey(address newGovKey) external;

    function setCommKeyWithAggKey(SigData calldata sigData, address newCommKey) external;

    function setCommKeyWithCommKey(address newCommKey) external;

    function govAction(bytes32 message) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getAggregateKey() external view returns (Key memory);

    function getGovernanceKey() external view returns (address);

    function getCommunityKey() external view returns (address);

    function isNonceUsedByAggKey(uint256 nonce) external view returns (bool);

    function getLastValidateTime() external view returns (uint256);
}

abstract contract Shared is IShared {
    /// @dev The address used to indicate whether transfer should send native or a token
    address internal constant _NATIVE_ADDR = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;
    address internal constant _ZERO_ADDR = address(0);
    bytes32 internal constant _NULL = "";
    uint256 internal constant _E_18 = 1e18;

    /// @dev    Checks that a uint isn't zero/empty
    modifier nzUint(uint256 u) {
        require(u != 0, "Shared: uint input is empty");
        _;
    }

    /// @dev    Checks that an address isn't zero/empty
    modifier nzAddr(address a) {
        require(a != _ZERO_ADDR, "Shared: address input is empty");
        _;
    }

    /// @dev    Checks that a bytes32 isn't zero/empty
    modifier nzBytes32(bytes32 b) {
        require(b != _NULL, "Shared: bytes32 input is empty");
        _;
    }

    /// @dev    Checks that the pubKeyX is populated
    modifier nzKey(Key memory key) {
        require(key.pubKeyX != 0, "Shared: pubKeyX is empty");
        _;
    }
}

abstract contract SchnorrSECP256K1 {
    // See https://en.bitcoin.it/wiki/Secp256k1 for this constant.
    // Group order of secp256k1
    uint256 private constant Q =
        // solium-disable-next-line indentation
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141;
    // solium-disable-next-line zeppelin/no-arithmetic-operations
    uint256 private constant HALF_Q = (Q >> 1) + 1;

    /** **************************************************************************
      @notice verifySignature returns true iff passed a valid Schnorr signature.

      @dev See https://en.wikipedia.org/wiki/Schnorr_signature for reference.

      @dev In what follows, let d be your secret key, PK be your public key,
      PKx be the x ordinate of your public key, and PKyp be the parity bit for
      the y ordinate (i.e., 0 if PKy is even, 1 if odd.)
      **************************************************************************
      @dev TO CREATE A VALID SIGNATURE FOR THIS METHOD

      @dev First PKx must be less than HALF_Q. Then follow these instructions
           (see evm/test/schnorr_test.js, for an example of carrying them out):
      @dev 1. Hash the target message to a bytes32, called msgHash here, using
              keccak256

      @dev 2. Pick k uniformly and cryptographically securely randomly from
              {0,...,Q-1}. It is critical that k remains confidential, as your
              private key can be reconstructed from k and the signature.

      @dev 3. Compute k*g in the secp256k1 group, where g is the group
              generator. (This is the same as computing the public key from the
              secret key k. But it's OK if k*g's x ordinate is greater than
              HALF_Q.)

      @dev 4. Compute the ethereum address for k*g. This is the lower 160 bits
              of the keccak hash of the concatenated affine coordinates of k*g,
              as 32-byte big-endians. (For instance, you could pass k to
              ethereumjs-utils's privateToAddress to compute this, though that
              should be strictly a development convenience, not for handling
              live secrets, unless you've locked your javascript environment
              down very carefully.) Call this address
              nonceTimesGeneratorAddress.

      @dev 5. Compute e=uint256(keccak256(PKx as a 32-byte big-endian
                                        ‖ PKyp as a single byte
                                        ‖ msgHash
                                        ‖ nonceTimesGeneratorAddress))
              This value e is called "msgChallenge" in verifySignature's source
              code below. Here "‖" means concatenation of the listed byte
              arrays.

      @dev 6. Let d be your secret key. Compute s = (k - d * e) % Q. Add Q to
              it, if it's negative. This is your signature. (d is your secret
              key.)
      **************************************************************************
      @dev TO VERIFY A SIGNATURE

      @dev Given a signature (s, e) of msgHash, constructed as above, compute
      S=e*PK+s*generator in the secp256k1 group law, and then the ethereum
      address of S, as described in step 4. Call that
      nonceTimesGeneratorAddress. Then call the verifySignature method as:

      @dev    verifySignature(PKx, PKyp, s, msgHash,
                              nonceTimesGeneratorAddress)
      **************************************************************************
      @dev This signging scheme deviates slightly from the classical Schnorr
      signature, in that the address of k*g is used in place of k*g itself,
      both when calculating e and when verifying sum S as described in the
      verification paragraph above. This reduces the difficulty of
      brute-forcing a signature by trying random secp256k1 points in place of
      k*g in the signature verification process from 256 bits to 160 bits.
      However, the difficulty of cracking the public key using "baby-step,
      giant-step" is only 128 bits, so this weakening constitutes no compromise
      in the security of the signatures or the key.

      @dev The constraint signingPubKeyX < HALF_Q comes from Eq. (281), p. 24
      of Yellow Paper version 78d7b9a. ecrecover only accepts "s" inputs less
      than HALF_Q, to protect against a signature- malleability vulnerability in
      ECDSA. Schnorr does not have this vulnerability, but we must account for
      ecrecover's defense anyway. And since we are abusing ecrecover by putting
      signingPubKeyX in ecrecover's "s" argument the constraint applies to
      signingPubKeyX, even though it represents a value in the base field, and
      has no natural relationship to the order of the curve's cyclic group.
      **************************************************************************
      @param msgHash is a 256-bit hash of the message being signed.
      @param signature is the actual signature, described as s in the above
             instructions.
      @param signingPubKeyX is the x ordinate of the public key. This must be
             less than HALF_Q.
      @param pubKeyYParity is 0 if the y ordinate of the public key is even, 1
             if it's odd.
      @param nonceTimesGeneratorAddress is the ethereum address of k*g in the
             above instructions
      **************************************************************************
      @return True if passed a valid signature, false otherwise. */

    function verifySignature(
        bytes32 msgHash,
        uint256 signature,
        uint256 signingPubKeyX,
        uint8 pubKeyYParity,
        address nonceTimesGeneratorAddress
    ) internal pure returns (bool) {
        require(signingPubKeyX < HALF_Q, "Public-key x >= HALF_Q");
        // Avoid signature malleability from multiple representations for ℤ/Qℤ elts
        require(signature < Q, "Sig must be reduced modulo Q");

        // Forbid trivial inputs, to avoid ecrecover edge cases. The main thing to
        // avoid is something which causes ecrecover to return 0x0: then trivial
        // signatures could be constructed with the nonceTimesGeneratorAddress input
        // set to 0x0.
        //
        // solium-disable-next-line indentation
        require(
            nonceTimesGeneratorAddress != address(0) && signingPubKeyX > 0 && signature > 0 && msgHash > 0,
            "No zero inputs allowed"
        );

        uint256 msgChallenge = uint256(
            keccak256(abi.encodePacked(signingPubKeyX, pubKeyYParity, msgHash, nonceTimesGeneratorAddress))
        );

        // Verify msgChallenge * signingPubKey + signature * generator ==
        //        nonce * generator
        //
        // https://ethresear.ch/t/you-can-kinda-abuse-ecrecover-to-do-ecmul-in-secp256k1-today/2384/9
        // The point corresponding to the address returned by
        // ecrecover(-s*r,v,r,e*r) is (r⁻¹ mod Q)*(e*r*R-(-s)*r*g)=e*R+s*g, where R
        // is the (v,r) point. See https://crypto.stackexchange.com/a/18106
        //
        // solium-disable-next-line indentation
        address recoveredAddress = ecrecover(
            // solium-disable-next-line zeppelin/no-arithmetic-operations
            bytes32(Q - mulmod(signingPubKeyX, signature, Q)),
            // https://ethereum.github.io/yellowpaper/paper.pdf p. 24, "The
            // value 27 represents an even y value and 28 represents an odd
            // y value."
            (pubKeyYParity == 0) ? 27 : 28,
            bytes32(signingPubKeyX),
            bytes32(mulmod(msgChallenge, signingPubKeyX, Q))
        );
        require(recoveredAddress != address(0), "Schnorr: recoveredAddress is 0");

        return nonceTimesGeneratorAddress == recoveredAddress;
    }

    function verifySigningKeyX(uint256 signingPubKeyX) internal pure {
        require(signingPubKeyX < HALF_Q, "Public-key x >= HALF_Q");
    }
}

contract KeyManager is SchnorrSECP256K1, Shared, IKeyManager {
    uint256 private constant _AGG_KEY_TIMEOUT = 2 days;

    /// @dev    The current (schnorr) aggregate key.
    Key private _aggKey;
    /// @dev    The current governance key.
    address private _govKey;
    /// @dev    The current community key.
    address private _commKey;
    /// @dev    The last time that a sig was verified (used for a dead man's switch)
    uint256 private _lastValidateTime;
    mapping(uint256 => bool) private _isNonceUsedByAggKey;

    constructor(
        Key memory initialAggKey,
        address initialGovKey,
        address initialCommKey
    ) nzAddr(initialGovKey) nzAddr(initialCommKey) nzKey(initialAggKey) validAggKey(initialAggKey) {
        _aggKey = initialAggKey;
        _govKey = initialGovKey;
        _commKey = initialCommKey;
        _lastValidateTime = block.timestamp;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Checks the validity of a signature and msgHash, then updates _lastValidateTime
     * @dev     It would be nice to split this up, but these checks
     *          need to be made atomicly always. This needs to be available
     *          in this contract and in the Vault etc
     * @param sigData   Struct containing the signature data over the message
     *                  to verify, signed by the aggregate key.
     * @param msgHash   The hash of the message being signed. The hash of the function
     *                  call parameters is concatenated and hashed together with the nonce, the
     *                  address of the caller, the chainId, and the address of this contract.
     */
    function _consumeKeyNonce(SigData calldata sigData, bytes32 msgHash) internal {
        Key memory key = _aggKey;

        require(
            verifySignature(msgHash, sigData.sig, key.pubKeyX, key.pubKeyYParity, sigData.kTimesGAddress),
            "KeyManager: Sig invalid"
        );
        require(!_isNonceUsedByAggKey[sigData.nonce], "KeyManager: nonce already used");

        _lastValidateTime = block.timestamp;
        _isNonceUsedByAggKey[sigData.nonce] = true;

        // Disable because tx.origin is not being used in the logic
        // solhint-disable-next-line avoid-tx-origin
        emit SignatureAccepted(sigData, tx.origin);
    }

    /**
     * @notice  Concatenates the contractMsgHash with the nonce, the address of the caller,
     *          the chainId, and the address of this contract, then hashes that and verifies the
     *          signature. This is done to prevent replay attacks.
     * @param sigData           Struct containing the signature data over the message
     *                          to verify, signed by the aggregate key.
     * @param contractMsgHash   The hash of the function's call parameters. This will be hashed
     *                          over other parameters to prevent replay attacks.
     */
    function consumeKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) external override {
        bytes32 msgHash = keccak256(
            abi.encode(contractMsgHash, sigData.nonce, msg.sender, block.chainid, address(this))
        );
        _consumeKeyNonce(sigData, msgHash);
    }

    /**
     * @notice  Set a new aggregate key. Requires a signature from the current aggregate key
     * @param sigData   Struct containing the signature data over the message
     *                  to verify, signed by the aggregate key.
     * @param newAggKey The new aggregate key to be set. The x component of the pubkey (uint256),
     *                  the parity of the y component (uint8)
     */
    function setAggKeyWithAggKey(
        SigData calldata sigData,
        Key calldata newAggKey
    )
        external
        override
        nzKey(newAggKey)
        validAggKey(newAggKey)
        consumeKeyNonceKeyManager(sigData, keccak256(abi.encode(this.setAggKeyWithAggKey.selector, newAggKey)))
    {
        emit AggKeySetByAggKey(_aggKey, newAggKey);
        _aggKey = newAggKey;
    }

    /**
     * @notice  Set a new aggregate key. Can only be called by the current governance key
     * @param newAggKey The new aggregate key to be set. The x component of the pubkey (uint256),
     *                  the parity of the y component (uint8)
     */
    function setAggKeyWithGovKey(
        Key calldata newAggKey
    ) external override nzKey(newAggKey) validAggKey(newAggKey) timeoutEmergency onlyGovernor {
        emit AggKeySetByGovKey(_aggKey, newAggKey);
        _aggKey = newAggKey;
    }

    /**
     * @notice  Set a new aggregate key. Requires a signature from the current aggregate key
     * @param sigData   Struct containing the signature data over the message
     *                  to verify, signed by the aggregate key.
     * @param newGovKey The new governance key to be set.

     */
    function setGovKeyWithAggKey(
        SigData calldata sigData,
        address newGovKey
    )
        external
        override
        nzAddr(newGovKey)
        consumeKeyNonceKeyManager(sigData, keccak256(abi.encode(this.setGovKeyWithAggKey.selector, newGovKey)))
    {
        emit GovKeySetByAggKey(_govKey, newGovKey);
        _govKey = newGovKey;
    }

    /**
     * @notice  Set a new governance key. Can only be called by current governance key
     * @param newGovKey    The new governance key to be set.
     */
    function setGovKeyWithGovKey(address newGovKey) external override nzAddr(newGovKey) onlyGovernor {
        emit GovKeySetByGovKey(_govKey, newGovKey);
        _govKey = newGovKey;
    }

    /**
     * @notice  Set a new community key. Requires a signature from the current aggregate key
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param newCommKey The new community key to be set.

     */
    function setCommKeyWithAggKey(
        SigData calldata sigData,
        address newCommKey
    )
        external
        override
        nzAddr(newCommKey)
        consumeKeyNonceKeyManager(sigData, keccak256(abi.encode(this.setCommKeyWithAggKey.selector, newCommKey)))
    {
        emit CommKeySetByAggKey(_commKey, newCommKey);
        _commKey = newCommKey;
    }

    /**
     * @notice  Update the Community Key. Can only be called by the current Community Key.
     * @param newCommKey   New Community key address.
     */
    function setCommKeyWithCommKey(address newCommKey) external override onlyCommunityKey nzAddr(newCommKey) {
        emit CommKeySetByCommKey(_commKey, newCommKey);
        _commKey = newCommKey;
    }

    /**
     * @notice Emit an event containing an action message. Can only be called by the governor.
     */
    function govAction(bytes32 message) external override onlyGovernor {
        emit GovernanceAction(message);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the current aggregate key
     * @return  The Key struct for the aggregate key
     */
    function getAggregateKey() external view override returns (Key memory) {
        return _aggKey;
    }

    /**
     * @notice  Get the current governance key
     * @return  The Key struct for the governance key
     */
    function getGovernanceKey() external view override returns (address) {
        return _getGovernanceKey();
    }

    /**
     * @notice  Get the current community key
     * @return  The Key struct for the community key
     */
    function getCommunityKey() external view override returns (address) {
        return _getCommunityKey();
    }

    /**
     * @notice  Get the last time that a function was called which
     *          required a signature from _aggregateKeyData or _governanceKeyData
     * @return  The last time consumeKeyNonce was called, in unix time (uint256)
     */
    function getLastValidateTime() external view override returns (uint256) {
        return _lastValidateTime;
    }

    /**
     * @notice  Get whether or not the specific keyID has used this nonce before
     *          since it cannot be used again
     * @return  Whether the nonce has already been used (bool)
     */
    function isNonceUsedByAggKey(uint256 nonce) external view override returns (bool) {
        return _isNonceUsedByAggKey[nonce];
    }

    /**
     * @notice  Get the current governance key
     * @return  The Key struct for the governance key
     */
    function _getGovernanceKey() internal view returns (address) {
        return _govKey;
    }

    /**
     * @notice  Get the current community key
     * @return  The Key struct for the community key
     */
    function _getCommunityKey() internal view returns (address) {
        return _commKey;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Check that enough time has passed for setAggKeyWithGovKey. Needs
    ///         to be done as a modifier so that it can happen before consumeKeyNonce
    modifier timeoutEmergency() {
        require(block.timestamp - _lastValidateTime >= _AGG_KEY_TIMEOUT, "KeyManager: not enough time");
        _;
    }

    /// @dev    Check that an aggregate key is capable of having its signatures
    ///         verified by the schnorr lib.
    modifier validAggKey(Key memory key) {
        verifySigningKeyX(key.pubKeyX);
        _;
    }

    /// @dev    Check that the sender is the governance address
    modifier onlyGovernor() {
        require(msg.sender == _getGovernanceKey(), "KeyManager: not governor");
        _;
    }

    /// @dev    Check that the caller is the Community Key address.
    modifier onlyCommunityKey() {
        require(msg.sender == _getCommunityKey(), "KeyManager: not Community Key");
        _;
    }

    /// @dev    For functions in this contract that require a signature from the aggregate key
    //          the msg.sender can't be hashed as anyone can make the call. Instead the
    //          address of this contract is used as the sender and hashed in the message.
    modifier consumeKeyNonceKeyManager(SigData calldata sigData, bytes32 contractMsgHash) {
        bytes32 msgHash = keccak256(
            abi.encode(contractMsgHash, sigData.nonce, address(this), block.chainid, address(this))
        );
        _consumeKeyNonce(sigData, msgHash);
        _;
    }
}

interface IHevm {
    // Set block.timestamp to newTimestamp
    function warp(uint256 newTimestamp) external;

    // Set block.number to newNumber
    function roll(uint256 newNumber) external;

    // Loads a storage slot from an address
    function load(address where, bytes32 slot) external returns (bytes32);

    // Stores a value to an address' storage slot
    function store(address where, bytes32 slot, bytes32 value) external;

    // Signs data (privateKey, digest) => (r, v, s)
    function sign(uint256 privateKey, bytes32 digest) external returns (uint8 r, bytes32 v, bytes32 s);

    // Gets address for a given private key
    function addr(uint256 privateKey) external returns (address addr);

    // Performs a foreign function call via terminal
    function ffi(string[] calldata inputs) external returns (bytes memory result);

    // Performs the next smart contract call with specified `msg.sender`
    function prank(address newSender) external;
}

interface IGovernanceCommunityGuarded is IShared {
    event CommunityGuardDisabled(bool communityGuardDisabled);
    event Suspended(bool suspended);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////
    /**
     * @notice  Enable Community Guard
     */

    function enableCommunityGuard() external;

    /**
     * @notice  Disable Community Guard
     */
    function disableCommunityGuard() external;

    /**
     * @notice  Can be used to suspend contract execution - only executable by
     *          governance and only to be used in case of emergency.
     */
    function suspend() external;

    /**
     * @notice      Resume contract execution
     */
    function resume() external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the Community Key
     * @return  The CommunityKey
     */
    function getCommunityKey() external view returns (address);

    /**
     * @notice  Get the Community Guard state
     * @return  The Community Guard state
     */
    function getCommunityGuardDisabled() external view returns (bool);

    /**
     * @notice  Get suspended state
     * @return  The suspended state
     */
    function getSuspendedState() external view returns (bool);

    /**
     * @notice  Get governor address
     * @return  The governor address
     */
    function getGovernor() external view returns (address);
}

abstract contract GovernanceCommunityGuarded is Shared, IGovernanceCommunityGuarded {
    /// @dev    Community Guard Disabled
    bool private _communityGuardDisabled;

    /// @dev    Whether execution is suspended
    bool private _suspended = false;

    /**
     * @notice  Get the governor's address. The contracts inheriting this (StateChainGateway and Vault)
     *          get the governor's address from the KeyManager through the AggKeyNonceConsumer's
     *          inheritance. Therefore, the implementation of this function must be left
     *          to the children. This is not implemented as a virtual onlyGovernor modifier to force
     *          the children to implement this function - virtual modifiers don't enforce that.
     * @return  The governor's address
     */
    function _getGovernor() internal view virtual returns (address);

    /**
     * @notice  Get the community's address. The contracts inheriting this (StateChainGateway and Vault)
     *          get the community's address from the KeyManager through the AggKeyNonceConsumer's
     *          inheritance. Therefore, the implementation of this function must be left
     *          to the children. This is not implemented as a virtual onlyCommunityKey modifier to force
     *          the children to implement this function - virtual modifiers don't enforce that.
     * @return  The community's address
     */
    function _getCommunityKey() internal view virtual returns (address);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Enable Community Guard
     */
    function enableCommunityGuard() external override onlyCommunityKey onlyCommunityGuardDisabled {
        _communityGuardDisabled = false;
        emit CommunityGuardDisabled(false);
    }

    /**
     * @notice  Disable Community Guard
     */
    function disableCommunityGuard() external override onlyCommunityKey onlyCommunityGuardEnabled {
        _communityGuardDisabled = true;
        emit CommunityGuardDisabled(true);
    }

    /**
     * @notice Can be used to suspend contract execution - only executable by
     * governance and only to be used in case of emergency.
     */
    function suspend() external override onlyGovernor onlyNotSuspended {
        _suspended = true;
        emit Suspended(true);
    }

    /**
     * @notice      Resume contract execution
     */
    function resume() external override onlyGovernor onlySuspended {
        _suspended = false;
        emit Suspended(false);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the Community Key
     * @return  The CommunityKey
     */
    function getCommunityKey() external view override returns (address) {
        return _getCommunityKey();
    }

    /**
     * @notice  Get the Community Guard state
     * @return  The Community Guard state
     */
    function getCommunityGuardDisabled() external view override returns (bool) {
        return _communityGuardDisabled;
    }

    /**
     * @notice  Get suspended state
     * @return  The suspended state
     */
    function getSuspendedState() external view override returns (bool) {
        return _suspended;
    }

    /**
     * @notice  Get governor address
     * @return  The governor address
     */
    function getGovernor() external view override returns (address) {
        return _getGovernor();
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                         Modifiers                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Check that the caller is the Community Key address.
    modifier onlyCommunityKey() {
        require(msg.sender == _getCommunityKey(), "Governance: not Community Key");
        _;
    }

    /// @dev    Check that community has disabled the community guard.
    modifier onlyCommunityGuardDisabled() {
        require(_communityGuardDisabled, "Governance: community guard enabled");
        _;
    }

    /// @dev    Check that community has disabled the community guard.
    modifier onlyCommunityGuardEnabled() {
        require(!_communityGuardDisabled, "Governance: community guard disabled");
        _;
    }

    /// @notice Ensure that the caller is the governor address. Calls the getGovernor
    ///         function which is implemented by the children.
    modifier onlyGovernor() {
        require(msg.sender == _getGovernor(), "Governance: not governor");
        _;
    }

    // @notice Check execution is suspended
    modifier onlySuspended() {
        require(_suspended, "Governance: not suspended");
        _;
    }

    // @notice Check execution is not suspended
    modifier onlyNotSuspended() {
        require(!_suspended, "Governance: suspended");
        _;
    }
}

interface IAggKeyNonceConsumer is IShared {
    event UpdatedKeyManager(address keyManager);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////
    /**
     * @notice  Update KeyManager reference. Used if KeyManager contract is updated
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param keyManager New KeyManager's address
     * @param omitChecks Allow the omission of the extra checks in a special case
     */
    function updateKeyManager(SigData calldata sigData, IKeyManager keyManager, bool omitChecks) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the KeyManager address/interface that's used to validate sigs
     * @return  The KeyManager (IKeyManager)
     */
    function getKeyManager() external view returns (IKeyManager);
}

abstract contract AggKeyNonceConsumer is Shared, IAggKeyNonceConsumer {
    /// @dev    The KeyManager used to checks sigs used in functions here
    IKeyManager private _keyManager;

    constructor(IKeyManager keyManager) nzAddr(address(keyManager)) {
        _keyManager = keyManager;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Update KeyManager reference. Used if KeyManager contract is updated
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param keyManager New KeyManager's address
     * @param omitChecks Allow the omission of the extra checks in a special case
     */
    function updateKeyManager(
        SigData calldata sigData,
        IKeyManager keyManager,
        bool omitChecks
    )
        external
        override
        nzAddr(address(keyManager))
        consumesKeyNonce(sigData, keccak256(abi.encode(this.updateKeyManager.selector, keyManager, omitChecks)))
    {
        // Check that the new KeyManager is a contract
        require(address(keyManager).code.length > 0);

        // Allow the child to check compatibility with the new KeyManager
        _checkUpdateKeyManager(keyManager, omitChecks);

        _keyManager = keyManager;
        emit UpdatedKeyManager(address(keyManager));
    }

    /// @dev   This will be called when upgrading to a new KeyManager. This allows the child's contract
    ///        to check its compatibility with the new KeyManager. This is to prevent the contract from
    //         getting bricked. There is no good way to enforce the implementation of consumeKeyNonce().
    function _checkUpdateKeyManager(IKeyManager keyManager, bool omitChecks) internal view virtual;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Getters                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the KeyManager address/interface that's used to validate sigs
     * @return  The KeyManager (IKeyManager)
     */
    function getKeyManager() public view override returns (IKeyManager) {
        return _keyManager;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                         Modifiers                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Calls consumeKeyNonce in _keyManager
    modifier consumesKeyNonce(SigData calldata sigData, bytes32 contractMsgHash) {
        getKeyManager().consumeKeyNonce(sigData, contractMsgHash);
        _;
    }
}

interface IFLIP is IERC20 {
    event IssuerUpdated(address oldIssuer, address newIssuer);

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function mint(address account, uint amount) external;

    function burn(address account, uint amount) external;

    function updateIssuer(address newIssuer) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function getIssuer() external view returns (address);
}

interface IFlipIssuer {
    /**
     * @notice  Get the FLIP token address
     * @return  The address of FLIP
     */
    function getFLIP() external view returns (IFLIP);
}

interface IStateChainGateway is IGovernanceCommunityGuarded, IFlipIssuer, IAggKeyNonceConsumer {
    event Funded(bytes32 indexed nodeID, uint256 amount, address funder);
    event RedemptionRegistered(
        bytes32 indexed nodeID,
        uint256 amount,
        address indexed redeemAddress,
        uint48 startTime,
        uint48 expiryTime
    );
    event RedemptionExecuted(bytes32 indexed nodeID, uint256 amount);
    event RedemptionExpired(bytes32 indexed nodeID, uint256 amount);
    event MinFundingChanged(uint256 oldMinFunding, uint256 newMinFunding);
    event GovernanceWithdrawal(address to, uint256 amount);
    event FLIPSet(address flip);
    event FlipSupplyUpdated(uint256 oldSupply, uint256 newSupply, uint256 stateChainBlockNumber);

    struct Redemption {
        uint256 amount;
        address redeemAddress;
        // 48 so that 160 (from redeemAddress) + 48 + 48 is 256 they can all be packed
        // into a single 256 bit slot
        uint48 startTime;
        uint48 expiryTime;
    }

    /**
     * @notice  Sets the FLIP address after initialization. We can't do this in the constructor
     *          because FLIP contract requires this contract's address on deployment for minting.
     *          First this contract is deployed, then the FLIP contract and finally setFLIP
     *          should be called. OnlyDeployer modifer for added security since tokens will be
     *          minted to this contract before calling setFLIP.
     * @param flip FLIP token address
     */
    function setFlip(IFLIP flip) external;

    /**
     * @notice          Add FLIP funds to a StateChain account identified with a nodeID
     * @dev             Requires the funder to have called `approve` in FLIP
     * @param amount    The amount of FLIP tokens
     * @param nodeID    The nodeID of the account to fund
     */
    function fundStateChainAccount(bytes32 nodeID, uint256 amount) external;

    /**
     * @notice  Redeem FLIP from the StateChain. The State Chain will determine the amount
     *          that can be redeemed, but a basic calculation for a validator would be:
     *          amount redeemable = stake + rewards - penalties.
     * @param sigData   Struct containing the signature data over the message
     *                  to verify, signed by the aggregate key.
     * @param nodeID    The nodeID of the account redeeming the FLIP
     * @param amount    The amount of funds to be locked up
     * @param redeemAddress    The redeemAddress who will receive the FLIP
     * @param expiryTime   The last valid timestamp that can execute this redemption (uint48)
     */
    function registerRedemption(
        SigData calldata sigData,
        bytes32 nodeID,
        uint256 amount,
        address redeemAddress,
        uint48 expiryTime
    ) external;

    /**
     * @notice  Execute a pending redemption to get back funds. Cannot execute a pending
     *          redemption before 48h have passed after registering it, or after the specified
     *          expiry time
     * @dev     No need for nzUint(nodeID) since that is handled by `redemption.expiryTime > 0`
     * @param nodeID    The nodeID of the account redeeming the FLIP
     */
    function executeRedemption(bytes32 nodeID) external;

    /**
     * @notice  Compares a given new FLIP supply against the old supply and mints or burns
     *          FLIP tokens from this contract as appropriate.
     *          It requires a message signed by the aggregate key.
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param newTotalSupply        new total supply of FLIP
     * @param stateChainBlockNumber State Chain block number for the new total supply
     */
    function updateFlipSupply(SigData calldata sigData, uint256 newTotalSupply, uint256 stateChainBlockNumber) external;

    /**
     * @notice  Updates the address that is allowed to issue FLIP tokens. This will be used when this
     *          contract needs an upgrade. A new contract will be deployed and all the FLIP will be
     *          transferred to it via the redemption process. Finally the right to issue FLIP will be transferred.
     * @param sigData     Struct containing the signature data over the message
     *                    to verify, signed by the aggregate key.
     * @param newIssuer   New contract that will issue FLIP tokens.
     * @param omitChecks Allow the omission of the extra checks in a special case
     */
    function updateFlipIssuer(SigData calldata sigData, address newIssuer, bool omitChecks) external;

    /**
     * @notice      Set the minimum amount of funds needed for `fundStateChainAccount` to be able
     *              to be called. Used to prevent spamming of funding.
     * @param newMinFunding   The new minimum funding amount
     */
    function setMinFunding(uint256 newMinFunding) external;

    /**
     * @notice Withdraw all FLIP to governance address in case of emergency. This withdrawal needs
     *         to be approved by the Community, it is a last resort. Used to rectify an emergency.
     *         The governance address is also updated as the issuer of FLIP.
     */
    function govWithdraw() external;

    /**
     * @notice Update the FLIP Issuer address with the governance address in case of emergency.
     *         This needs to be approved by the Community, it is a last resort. Used to rectify
     *         an emergency.
     */
    function govUpdateFlipIssuer() external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the minimum amount of funds that's required for funding
     *          an account on the StateChain.
     * @return  The minimum amount (uint)
     */
    function getMinimumFunding() external view returns (uint256);

    /**
     * @notice  Get the pending redemption for the input nodeID. If there was never
     *          a pending redemption for this nodeID, or it has already been executed
     *          (and therefore deleted), it'll return (0, 0x00..., 0, 0)
     * @param nodeID   The nodeID which has a pending redemption
     * @return         The redemption (Redemption struct)
     */
    function getPendingRedemption(bytes32 nodeID) external view returns (Redemption memory);

    /**
     * @notice  Get the last state chain block number that the supply was updated at
     * @return  The state chain block number of the last update
     */
    function getLastSupplyUpdateBlockNumber() external view returns (uint256);
}

contract StateChainGateway is IFlipIssuer, IStateChainGateway, AggKeyNonceConsumer, GovernanceCommunityGuarded {
    /// @dev    The FLIP token address. To be set only once after deployment via setFlip.
    // solhint-disable-next-line var-name-mixedcase
    IFLIP private _FLIP;

    /// @dev    The minimum amount of FLIP needed to fund an account, to prevent spamming
    uint256 private _minFunding;
    /// @dev    Holding pending redemptions for the 48h withdrawal delay
    mapping(bytes32 => Redemption) private _pendingRedemptions;
    /// @dev   Time after registerRedemption required to wait before call to executeRedemption
    uint48 public constant REDEMPTION_DELAY = 2 days;

    /// @dev    The last block number in which the State Chain updated the totalSupply
    uint256 private _lastSupplyUpdateBlockNum = 0;

    // Defined in IStateChainGateway, just here for convenience
    // struct Redemption {
    //     uint amount;
    //     address redeemAddress;
    //     // 48 so that 160 (from redeemAddress) + 48 + 48 is 256 they can all be packed
    //     // into a single 256 bit slot
    //     uint48 startTime;
    //     uint48 expiryTime;
    // }

    constructor(IKeyManager keyManager, uint256 minFunding) AggKeyNonceConsumer(keyManager) {
        _minFunding = minFunding;
    }

    /// @dev   Get the governor address from the KeyManager. This is called by the onlyGovernor
    ///        modifier in the GovernanceCommunityGuarded. This logic can't be moved to the
    ///        GovernanceCommunityGuarded since it requires a reference to the KeyManager.
    function _getGovernor() internal view override returns (address) {
        return getKeyManager().getGovernanceKey();
    }

    /// @dev   Get the community key from the KeyManager. This is called by the isCommunityKey
    ///        modifier in the GovernanceCommunityGuarded. This logic can't be moved to the
    ///        GovernanceCommunityGuarded since it requires a reference to the KeyManager.
    function _getCommunityKey() internal view override returns (address) {
        return getKeyManager().getCommunityKey();
    }

    /**
     * @notice  Get the FLIP token address
     * @dev     This function and it's return value will be checked when updating the FLIP issuer.
     *          Do not remove nor modify this function in future versions of this contract.
     * @return  The address of FLIP
     */
    function getFLIP() external view override returns (IFLIP) {
        return _FLIP;
    }

    /// @dev   Ensure that a new keyManager has the getGovernanceKey() and getCommunityKey()
    ///        functions implemented. These are functions required for this contract to
    ///        to at least be able to use the emergency mechanism.
    function _checkUpdateKeyManager(IKeyManager keyManager, bool omitChecks) internal view override {
        address newGovKey = keyManager.getGovernanceKey();
        address newCommKey = keyManager.getCommunityKey();

        if (!omitChecks) {
            // Ensure that the keys are the same
            require(newGovKey == _getGovernor() && newCommKey == _getCommunityKey());

            Key memory newAggKey = keyManager.getAggregateKey();
            Key memory currentAggKey = getKeyManager().getAggregateKey();

            require(
                newAggKey.pubKeyX == currentAggKey.pubKeyX && newAggKey.pubKeyYParity == currentAggKey.pubKeyYParity
            );
        } else {
            // Check that the addresses have been initialized
            require(newGovKey != address(0) && newCommKey != address(0));
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Sets the FLIP address after initialization. We can't do this in the constructor
     *          because FLIP contract requires this contract's address on deployment for minting.
     *          First this contract is deployed, then the FLIP contract and finally setFLIP
     *          should be called. Deployed via DeployerContract.sol so it can't be frontrun.
     *          The FLIP address can only be set once.
     * @param flip FLIP token address
     */
    function setFlip(IFLIP flip) external override nzAddr(address(flip)) {
        require(address(_FLIP) == address(0), "Gateway: Flip address already set");
        _FLIP = flip;
        emit FLIPSet(address(flip));
    }

    /**
     * @notice          Add FLIP funds to a StateChain account identified with a nodeID
     * @dev             Requires the funder to have called `approve` in FLIP
     * @param amount    The amount of FLIP tokens
     * @param nodeID    The nodeID of the account to fund
     */
    function fundStateChainAccount(bytes32 nodeID, uint256 amount) external override nzBytes32(nodeID) {
        IFLIP flip = _FLIP;
        require(address(flip) != address(0), "Gateway: Flip not set");
        require(amount >= _minFunding, "Gateway: not enough funds");
        // Assumption of set token allowance by the user
        flip.transferFrom(msg.sender, address(this), amount);
        emit Funded(nodeID, amount, msg.sender);
    }

    /**
     * @notice  Redeem FLIP from the StateChain. The State Chain will determine the amount
     *          that can be redeemed, but a basic calculation for a validator would be:
     *          amount redeemable = stake + rewards - penalties.
     * @param sigData   Struct containing the signature data over the message
     *                  to verify, signed by the aggregate key.
     * @param nodeID    The nodeID of the account redeeming the FLIP
     * @param amount    The amount of funds to be locked up
     * @param redeemAddress    The redeemAddress who will receive the FLIP
     * @param expiryTime   The last valid timestamp that can execute this redemption (uint48)
     */
    function registerRedemption(
        SigData calldata sigData,
        bytes32 nodeID,
        uint256 amount,
        address redeemAddress,
        uint48 expiryTime
    )
        external
        override
        onlyNotSuspended
        nzBytes32(nodeID)
        nzUint(amount)
        nzAddr(redeemAddress)
        consumesKeyNonce(
            sigData,
            keccak256(abi.encode(this.registerRedemption.selector, nodeID, amount, redeemAddress, expiryTime))
        )
    {
        require(
            // Must be fresh or have been executed & deleted, or past the expiry
            block.timestamp > uint256(_pendingRedemptions[nodeID].expiryTime),
            "Gateway: a pending redemption exists"
        );

        uint48 startTime = uint48(block.timestamp) + REDEMPTION_DELAY;
        require(expiryTime > startTime, "Gateway: expiry time too soon");

        _pendingRedemptions[nodeID] = Redemption(amount, redeemAddress, startTime, expiryTime);
        emit RedemptionRegistered(nodeID, amount, redeemAddress, startTime, expiryTime);
    }

    /**
     * @notice  Execute a pending redemption to get back funds. Cannot execute a pending
     *          redemption before 48h have passed after registering it, or after the specified
     *          expiry time
     * @dev     No need for nzUint(nodeID) since that is handled by `redemption.expiryTime > 0`
     * @param nodeID    The nodeID of the funder
     */
    function executeRedemption(bytes32 nodeID) external override onlyNotSuspended {
        Redemption memory redemption = _pendingRedemptions[nodeID];
        require(
            block.timestamp >= redemption.startTime && redemption.expiryTime > 0,
            "Gateway: early or already execd"
        );

        // Housekeeping
        delete _pendingRedemptions[nodeID];

        if (block.timestamp <= redemption.expiryTime) {
            emit RedemptionExecuted(nodeID, redemption.amount);

            // Send the tokens
            _FLIP.transfer(redemption.redeemAddress, redemption.amount);
        } else {
            emit RedemptionExpired(nodeID, redemption.amount);
        }
    }

    /**
     * @notice  Compares a given new FLIP supply against the old supply and mints or burns
     *          FLIP tokens from this contract as appropriate.
     *          It requires a message signed by the aggregate key.
     * @dev     Hardcoded to only mint and burn FLIP tokens to/from this contract.
     * @param sigData               Struct containing the signature data over the message
     *                              to verify, signed by the aggregate key.
     * @param newTotalSupply        new total supply of FLIP
     * @param stateChainBlockNumber State Chain block number for the new total supply
     */
    function updateFlipSupply(
        SigData calldata sigData,
        uint256 newTotalSupply,
        uint256 stateChainBlockNumber
    )
        external
        override
        onlyNotSuspended
        nzUint(newTotalSupply)
        consumesKeyNonce(
            sigData,
            keccak256(abi.encode(this.updateFlipSupply.selector, newTotalSupply, stateChainBlockNumber))
        )
    {
        require(stateChainBlockNumber > _lastSupplyUpdateBlockNum, "Gateway: old FLIP supply update");
        _lastSupplyUpdateBlockNum = stateChainBlockNumber;
        IFLIP flip = _FLIP;
        uint256 oldSupply = flip.totalSupply();
        if (newTotalSupply < oldSupply) {
            uint256 amount = oldSupply - newTotalSupply;
            flip.burn(address(this), amount);
        } else if (newTotalSupply > oldSupply) {
            uint256 amount = newTotalSupply - oldSupply;
            flip.mint(address(this), amount);
        }
        emit FlipSupplyUpdated(oldSupply, newTotalSupply, stateChainBlockNumber);
    }

    /**
     * @notice  Updates the address that is allowed to issue FLIP tokens. This will be used when this
     *          contract needs an upgrade. A new contract will be deployed and all the FLIP will be
     *          transferred to it via the redemption process. Finally the right to issue FLIP will be transferred.
     * @dev     The new issuer must be a contract and, in a standard upgrade, it must have the reference FLIP address.
     *          In a special case where the check is omitted, the new issuer must be a contract, never an EOA.
     * @param sigData     Struct containing the signature data over the message
     *                    to verify, signed by the aggregate key.
     * @param newIssuer   New contract that will issue FLIP tokens.
     * @param omitChecks Allow the omission of the extra checks in a special case
     */
    function updateFlipIssuer(
        SigData calldata sigData,
        address newIssuer,
        bool omitChecks
    )
        external
        override
        onlyNotSuspended
        nzAddr(newIssuer)
        consumesKeyNonce(sigData, keccak256(abi.encode(this.updateFlipIssuer.selector, newIssuer, omitChecks)))
    {
        if (!omitChecks) {
            require(IFlipIssuer(newIssuer).getFLIP() == _FLIP, "Gateway: wrong FLIP ref");
        } else {
            require(newIssuer.code.length > 0);
        }

        _FLIP.updateIssuer(newIssuer);
    }

    /**
     * @notice      Set the minimum amount of funds needed for `fundStateChainAccount` to be able
     *              to be called. Used to prevent spamming of funding.
     * @param newMinFunding   The new minimum funding amount
     */
    function setMinFunding(uint256 newMinFunding) external override nzUint(newMinFunding) onlyGovernor {
        emit MinFundingChanged(_minFunding, newMinFunding);
        _minFunding = newMinFunding;
    }

    /**
     * @notice Withdraw all FLIP to governance address in case of emergency. This withdrawal needs
     *         to be approved by the Community, it is a last resort. Used to rectify an emergency.
     *         Transfer the issuance to the governance address if this contract is the issuer.
     */
    function govWithdraw() external override onlyGovernor onlyCommunityGuardDisabled onlySuspended {
        IFLIP flip = _FLIP;
        uint256 amount = flip.balanceOf(address(this));

        // Could use msg.sender or getGovernor() but hardcoding the get call just for extra safety
        address governor = getKeyManager().getGovernanceKey();
        flip.transfer(governor, amount);
        emit GovernanceWithdrawal(governor, amount);

        // Check issuer to ensure this doesn't revert
        if (flip.getIssuer() == address(this)) {
            flip.updateIssuer(governor);
        }
    }

    /**
     * @notice Update the FLIP Issuer address with the governance address in case of emergency.
     *         This needs to be approved by the Community, it is a last resort. Used to rectify
     *         an emergency.
     */
    function govUpdateFlipIssuer() external override onlyGovernor onlyCommunityGuardDisabled onlySuspended {
        address governor = getKeyManager().getGovernanceKey();
        _FLIP.updateIssuer(governor);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Get the minimum amount of funds that's required for funding
     *          an account on the StateChain.
     * @return  The minimum amount (uint)
     */
    function getMinimumFunding() external view override returns (uint256) {
        return _minFunding;
    }

    /**
     * @notice  Get the pending redemption for the input nodeID. If there was never
     *          a pending redemption for this nodeID, or it has already been executed
     *          (and therefore deleted), it'll return (0, 0x00..., 0, 0)
     * @param nodeID   The nodeID which has a pending redemption
     * @return         The redemption (Redemption struct)
     */
    function getPendingRedemption(bytes32 nodeID) external view override returns (Redemption memory) {
        return _pendingRedemptions[nodeID];
    }

    /**
     * @notice  Get the last state chain block number of the last supply update
     * @return  The state chain block number of the last supply update
     */
    function getLastSupplyUpdateBlockNumber() external view override returns (uint256) {
        return _lastSupplyUpdateBlockNum;
    }
}

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

interface IVault is IGovernanceCommunityGuarded, IAggKeyNonceConsumer {
    event TransferNativeFailed(address payable indexed recipient, uint256 amount);
    event TransferTokenFailed(address payable indexed recipient, uint256 amount, address indexed token, bytes reason);

    event SwapNative(
        uint32 dstChain,
        bytes dstAddress,
        uint32 dstToken,
        uint256 amount,
        address indexed sender,
        bytes cfParameters
    );
    event SwapToken(
        uint32 dstChain,
        bytes dstAddress,
        uint32 dstToken,
        address srcToken,
        uint256 amount,
        address indexed sender,
        bytes cfParameters
    );

    /// @dev bytes parameters is not indexed because indexing a dynamic type for it to be filtered
    ///      makes it so we won't be able to decode it unless we specifically search for it. If we want
    ///      to filter it and decode it then we would need to have both the indexed and the non-indexed
    ///      version in the event. That is unnecessary.
    event XCallNative(
        uint32 dstChain,
        bytes dstAddress,
        uint32 dstToken,
        uint256 amount,
        address indexed sender,
        bytes message,
        uint256 gasAmount,
        bytes cfParameters
    );
    event XCallToken(
        uint32 dstChain,
        bytes dstAddress,
        uint32 dstToken,
        address srcToken,
        uint256 amount,
        address indexed sender,
        bytes message,
        uint256 gasAmount,
        bytes cfParameters
    );

    event AddGasNative(bytes32 swapID, uint256 amount);
    event AddGasToken(bytes32 swapID, uint256 amount, address token);

    event ExecuteActionsFailed(
        address payable indexed multicallAddress,
        uint256 amount,
        address indexed token,
        bytes reason
    );

    function allBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray,
        FetchParams[] calldata fetchParamsArray,
        TransferParams[] calldata transferParamsArray
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Transfers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function transfer(SigData calldata sigData, TransferParams calldata transferParams) external;

    function transferBatch(SigData calldata sigData, TransferParams[] calldata transferParamsArray) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Fetch Deposits                    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function deployAndFetchBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray
    ) external;

    function fetchBatch(SigData calldata sigData, FetchParams[] calldata fetchParamsArray) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //         Initiate cross-chain swaps (source chain)        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function xSwapToken(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        IERC20 srcToken,
        uint256 amount,
        bytes calldata cfParameters
    ) external;

    function xSwapNative(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        bytes calldata cfParameters
    ) external payable;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //     Initiate cross-chain call and swap (source chain)    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function xCallNative(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        bytes calldata message,
        uint256 gasAmount,
        bytes calldata cfParameters
    ) external payable;

    function xCallToken(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        bytes calldata message,
        uint256 gasAmount,
        IERC20 srcToken,
        uint256 amount,
        bytes calldata cfParameters
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                     Gas topups                           //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function addGasNative(bytes32 swapID) external payable;

    function addGasToken(bytes32 swapID, uint256 amount, IERC20 token) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //      Execute cross-chain call and swap (dest. chain)     //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function executexSwapAndCall(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //          Execute cross-chain call (dest. chain)          //
    //                                                          //
    //////////////////////////////////////////////////////////////
    function executexCall(
        SigData calldata sigData,
        address recipient,
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                 Auxiliary chain actions                  //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function executeActions(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        IMulticall.Call[] calldata calls,
        uint256 gasMulticall
    ) external;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Governance                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    function govWithdraw(address[] calldata tokens) external;
}

interface IERC20Permit {
    /**
     * @dev Sets `value` as the allowance of `spender` over ``owner``'s tokens,
     * given ``owner``'s signed approval.
     *
     * IMPORTANT: The same issues {IERC20-approve} has related to transaction
     * ordering also apply here.
     *
     * Emits an {Approval} event.
     *
     * Requirements:
     *
     * - `spender` cannot be the zero address.
     * - `deadline` must be a timestamp in the future.
     * - `v`, `r` and `s` must be a valid `secp256k1` signature from `owner`
     * over the EIP712-formatted function arguments.
     * - the signature must use ``owner``'s current nonce (see {nonces}).
     *
     * For more information on the signature format, see the
     * https://eips.ethereum.org/EIPS/eip-2612#specification[relevant EIP
     * section].
     */
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external;

    /**
     * @dev Returns the current nonce for `owner`. This value must be
     * included whenever a signature is generated for {permit}.
     *
     * Every successful call to {permit} increases ``owner``'s nonce by one. This
     * prevents a signature from being used multiple times.
     */
    function nonces(address owner) external view returns (uint256);

    /**
     * @dev Returns the domain separator used in the encoding of the signature for {permit}, as defined by {EIP712}.
     */
    // solhint-disable-next-line func-name-mixedcase
    function DOMAIN_SEPARATOR() external view returns (bytes32);
}

library Address {
    /**
     * @dev Returns true if `account` is a contract.
     *
     * [IMPORTANT]
     * ====
     * It is unsafe to assume that an address for which this function returns
     * false is an externally-owned account (EOA) and not a contract.
     *
     * Among others, `isContract` will return false for the following
     * types of addresses:
     *
     *  - an externally-owned account
     *  - a contract in construction
     *  - an address where a contract will be created
     *  - an address where a contract lived, but was destroyed
     * ====
     *
     * [IMPORTANT]
     * ====
     * You shouldn't rely on `isContract` to protect against flash loan attacks!
     *
     * Preventing calls from contracts is highly discouraged. It breaks composability, breaks support for smart wallets
     * like Gnosis Safe, and does not provide security since it can be circumvented by calling from a contract
     * constructor.
     * ====
     */
    function isContract(address account) internal view returns (bool) {
        // This method relies on extcodesize/address.code.length, which returns 0
        // for contracts in construction, since the code is only stored at the end
        // of the constructor execution.

        return account.code.length > 0;
    }

    /**
     * @dev Replacement for Solidity's `transfer`: sends `amount` wei to
     * `recipient`, forwarding all available gas and reverting on errors.
     *
     * https://eips.ethereum.org/EIPS/eip-1884[EIP1884] increases the gas cost
     * of certain opcodes, possibly making contracts go over the 2300 gas limit
     * imposed by `transfer`, making them unable to receive funds via
     * `transfer`. {sendValue} removes this limitation.
     *
     * https://diligence.consensys.net/posts/2019/09/stop-using-soliditys-transfer-now/[Learn more].
     *
     * IMPORTANT: because control is transferred to `recipient`, care must be
     * taken to not create reentrancy vulnerabilities. Consider using
     * {ReentrancyGuard} or the
     * https://solidity.readthedocs.io/en/v0.5.11/security-considerations.html#use-the-checks-effects-interactions-pattern[checks-effects-interactions pattern].
     */
    function sendValue(address payable recipient, uint256 amount) internal {
        require(address(this).balance >= amount, "Address: insufficient balance");

        (bool success, ) = recipient.call{value: amount}("");
        require(success, "Address: unable to send value, recipient may have reverted");
    }

    /**
     * @dev Performs a Solidity function call using a low level `call`. A
     * plain `call` is an unsafe replacement for a function call: use this
     * function instead.
     *
     * If `target` reverts with a revert reason, it is bubbled up by this
     * function (like regular Solidity function calls).
     *
     * Returns the raw returned data. To convert to the expected return value,
     * use https://solidity.readthedocs.io/en/latest/units-and-global-variables.html?highlight=abi.decode#abi-encoding-and-decoding-functions[`abi.decode`].
     *
     * Requirements:
     *
     * - `target` must be a contract.
     * - calling `target` with `data` must not revert.
     *
     * _Available since v3.1._
     */
    function functionCall(address target, bytes memory data) internal returns (bytes memory) {
        return functionCallWithValue(target, data, 0, "Address: low-level call failed");
    }

    /**
     * @dev Same as {xref-Address-functionCall-address-bytes-}[`functionCall`], but with
     * `errorMessage` as a fallback revert reason when `target` reverts.
     *
     * _Available since v3.1._
     */
    function functionCall(
        address target,
        bytes memory data,
        string memory errorMessage
    ) internal returns (bytes memory) {
        return functionCallWithValue(target, data, 0, errorMessage);
    }

    /**
     * @dev Same as {xref-Address-functionCall-address-bytes-}[`functionCall`],
     * but also transferring `value` wei to `target`.
     *
     * Requirements:
     *
     * - the calling contract must have an ETH balance of at least `value`.
     * - the called Solidity function must be `payable`.
     *
     * _Available since v3.1._
     */
    function functionCallWithValue(address target, bytes memory data, uint256 value) internal returns (bytes memory) {
        return functionCallWithValue(target, data, value, "Address: low-level call with value failed");
    }

    /**
     * @dev Same as {xref-Address-functionCallWithValue-address-bytes-uint256-}[`functionCallWithValue`], but
     * with `errorMessage` as a fallback revert reason when `target` reverts.
     *
     * _Available since v3.1._
     */
    function functionCallWithValue(
        address target,
        bytes memory data,
        uint256 value,
        string memory errorMessage
    ) internal returns (bytes memory) {
        require(address(this).balance >= value, "Address: insufficient balance for call");
        (bool success, bytes memory returndata) = target.call{value: value}(data);
        return verifyCallResultFromTarget(target, success, returndata, errorMessage);
    }

    /**
     * @dev Same as {xref-Address-functionCall-address-bytes-}[`functionCall`],
     * but performing a static call.
     *
     * _Available since v3.3._
     */
    function functionStaticCall(address target, bytes memory data) internal view returns (bytes memory) {
        return functionStaticCall(target, data, "Address: low-level static call failed");
    }

    /**
     * @dev Same as {xref-Address-functionCall-address-bytes-string-}[`functionCall`],
     * but performing a static call.
     *
     * _Available since v3.3._
     */
    function functionStaticCall(
        address target,
        bytes memory data,
        string memory errorMessage
    ) internal view returns (bytes memory) {
        (bool success, bytes memory returndata) = target.staticcall(data);
        return verifyCallResultFromTarget(target, success, returndata, errorMessage);
    }

    /**
     * @dev Same as {xref-Address-functionCall-address-bytes-}[`functionCall`],
     * but performing a delegate call.
     *
     * _Available since v3.4._
     */
    function functionDelegateCall(address target, bytes memory data) internal returns (bytes memory) {
        return functionDelegateCall(target, data, "Address: low-level delegate call failed");
    }

    /**
     * @dev Same as {xref-Address-functionCall-address-bytes-string-}[`functionCall`],
     * but performing a delegate call.
     *
     * _Available since v3.4._
     */
    function functionDelegateCall(
        address target,
        bytes memory data,
        string memory errorMessage
    ) internal returns (bytes memory) {
        (bool success, bytes memory returndata) = target.delegatecall(data);
        return verifyCallResultFromTarget(target, success, returndata, errorMessage);
    }

    /**
     * @dev Tool to verify that a low level call to smart-contract was successful, and revert (either by bubbling
     * the revert reason or using the provided one) in case of unsuccessful call or if target was not a contract.
     *
     * _Available since v4.8._
     */
    function verifyCallResultFromTarget(
        address target,
        bool success,
        bytes memory returndata,
        string memory errorMessage
    ) internal view returns (bytes memory) {
        if (success) {
            if (returndata.length == 0) {
                // only check isContract if the call was successful and the return data is empty
                // otherwise we already know that it was a contract
                require(isContract(target), "Address: call to non-contract");
            }
            return returndata;
        } else {
            _revert(returndata, errorMessage);
        }
    }

    /**
     * @dev Tool to verify that a low level call was successful, and revert if it wasn't, either by bubbling the
     * revert reason or using the provided one.
     *
     * _Available since v4.3._
     */
    function verifyCallResult(
        bool success,
        bytes memory returndata,
        string memory errorMessage
    ) internal pure returns (bytes memory) {
        if (success) {
            return returndata;
        } else {
            _revert(returndata, errorMessage);
        }
    }

    function _revert(bytes memory returndata, string memory errorMessage) private pure {
        // Look for revert reason and bubble it up if present
        if (returndata.length > 0) {
            // The easiest way to bubble the revert reason is using memory via assembly
            /// @solidity memory-safe-assembly
            assembly {
                let returndata_size := mload(returndata)
                revert(add(32, returndata), returndata_size)
            }
        } else {
            revert(errorMessage);
        }
    }
}

library SafeERC20 {
    using Address for address;

    function safeTransfer(IERC20 token, address to, uint256 value) internal {
        _callOptionalReturn(token, abi.encodeWithSelector(token.transfer.selector, to, value));
    }

    function safeTransferFrom(IERC20 token, address from, address to, uint256 value) internal {
        _callOptionalReturn(token, abi.encodeWithSelector(token.transferFrom.selector, from, to, value));
    }

    /**
     * @dev Deprecated. This function has issues similar to the ones found in
     * {IERC20-approve}, and its usage is discouraged.
     *
     * Whenever possible, use {safeIncreaseAllowance} and
     * {safeDecreaseAllowance} instead.
     */
    function safeApprove(IERC20 token, address spender, uint256 value) internal {
        // safeApprove should only be called when setting an initial allowance,
        // or when resetting it to zero. To increase and decrease it, use
        // 'safeIncreaseAllowance' and 'safeDecreaseAllowance'
        require(
            (value == 0) || (token.allowance(address(this), spender) == 0),
            "SafeERC20: approve from non-zero to non-zero allowance"
        );
        _callOptionalReturn(token, abi.encodeWithSelector(token.approve.selector, spender, value));
    }

    function safeIncreaseAllowance(IERC20 token, address spender, uint256 value) internal {
        uint256 newAllowance = token.allowance(address(this), spender) + value;
        _callOptionalReturn(token, abi.encodeWithSelector(token.approve.selector, spender, newAllowance));
    }

    function safeDecreaseAllowance(IERC20 token, address spender, uint256 value) internal {
        unchecked {
            uint256 oldAllowance = token.allowance(address(this), spender);
            require(oldAllowance >= value, "SafeERC20: decreased allowance below zero");
            uint256 newAllowance = oldAllowance - value;
            _callOptionalReturn(token, abi.encodeWithSelector(token.approve.selector, spender, newAllowance));
        }
    }

    function safePermit(
        IERC20Permit token,
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) internal {
        uint256 nonceBefore = token.nonces(owner);
        token.permit(owner, spender, value, deadline, v, r, s);
        uint256 nonceAfter = token.nonces(owner);
        require(nonceAfter == nonceBefore + 1, "SafeERC20: permit did not succeed");
    }

    /**
     * @dev Imitates a Solidity high-level call (i.e. a regular function call to a contract), relaxing the requirement
     * on the return value: the return value is optional (but if data is returned, it must not be false).
     * @param token The token targeted by the call.
     * @param data The call data (encoded using abi.encode or one of its variants).
     */
    function _callOptionalReturn(IERC20 token, bytes memory data) private {
        // We need to perform a low level call here, to bypass Solidity's return data size checking mechanism, since
        // we're implementing it ourselves. We use {Address-functionCall} to perform this call, which verifies that
        // the target address contains contract code and also asserts for success in the low-level call.

        bytes memory returndata = address(token).functionCall(data, "SafeERC20: low-level call failed");
        if (returndata.length > 0) {
            // Return data is optional
            require(abi.decode(returndata, (bool)), "SafeERC20: ERC20 operation did not succeed");
        }
    }
}

interface ICFReceiver {
    /**
     * @notice  Receiver of a cross-chain swap and call made by the Chainflip Protocol.

     * @param srcChain      The source chain according to the Chainflip Protocol's nomenclature.
     * @param srcAddress    Bytes containing the source address on the source chain.
     * @param message       The message sent on the source chain. This is a general purpose message.
     * @param token         Address of the token received. _NATIVE_ADDR if native.
     * @param amount        Amount of tokens received. This will match msg.value for native tokens.
     */
    function cfReceive(
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) external payable;

    /**
     * @notice  Receiver of a cross-chain call made by the Chainflip Protocol.

     * @param srcChain      The source chain according to the Chainflip Protocol's nomenclature.
     * @param srcAddress    Bytes containing the source address on the source chain.
     * @param message       The message sent on the source chain. This is a general purpose message.
     */
    function cfReceivexCall(uint32 srcChain, bytes calldata srcAddress, bytes calldata message) external;
}

interface IERC20Lite {
    // Taken from OZ:
    /**
     * @dev Moves `amount` tokens from the caller's account to `recipient`.
     *
     * Emits a {Transfer} event.
     */
    function transfer(address, uint256) external;

    // Taken from OZ:
    /**
     * @dev Returns the amount of tokens owned by `account`.
     */
    function balanceOf(address) external view returns (uint256);
}

contract Deposit {
    address payable private immutable vault;

    constructor(IERC20Lite token) {
        vault = payable(msg.sender);
        if (address(token) == 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE) {
            // solhint-disable-next-line avoid-low-level-calls
            (bool success, ) = msg.sender.call{value: address(this).balance}("");
            require(success);
        } else {
            // Not checking the return value to avoid reverts for tokens with no return value.
            token.transfer(msg.sender, token.balanceOf(address(this)));
        }
    }

    function fetch(IERC20Lite token) external {
        require(msg.sender == vault);

        // Slightly cheaper to use msg.sender instead of Vault.
        if (address(token) == 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE) {
            // solhint-disable-next-line avoid-low-level-calls
            (bool success, ) = msg.sender.call{value: address(this).balance}("");
            require(success);
        } else {
            // IERC20Lite.transfer doesn't have a return bool to avoid reverts on non-standard ERC20s
            token.transfer(msg.sender, token.balanceOf(address(this)));
        }
    }

    receive() external payable {}
}

contract Vault is IVault, AggKeyNonceConsumer, GovernanceCommunityGuarded {
    using SafeERC20 for IERC20;

    uint256 private constant _AGG_KEY_EMERGENCY_TIMEOUT = 3 days;
    uint256 private constant _GAS_TO_FORWARD = 3500;

    constructor(IKeyManager keyManager) AggKeyNonceConsumer(keyManager) {}

    /// @dev   Get the governor address from the KeyManager. This is called by the onlyGovernor
    ///        modifier in the GovernanceCommunityGuarded. This logic can't be moved to the
    ///        GovernanceCommunityGuarded since it requires a reference to the KeyManager.
    function _getGovernor() internal view override returns (address) {
        return getKeyManager().getGovernanceKey();
    }

    /// @dev   Get the community key from the KeyManager. This is called by the isCommunityKey
    ///        modifier in the GovernanceCommunityGuarded. This logic can't be moved to the
    ///        GovernanceCommunityGuarded since it requires a reference to the KeyManager.
    function _getCommunityKey() internal view override returns (address) {
        return getKeyManager().getCommunityKey();
    }

    /// @dev   Ensure that a new keyManager has the getGovernanceKey(), getCommunityKey()
    ///        and getLastValidateTime() are implemented. These are functions required for
    ///        this contract to at least be able to use the emergency mechanism.
    function _checkUpdateKeyManager(IKeyManager keyManager, bool omitChecks) internal view override {
        address newGovKey = keyManager.getGovernanceKey();
        address newCommKey = keyManager.getCommunityKey();
        uint256 lastValidateTime = keyManager.getLastValidateTime();

        if (!omitChecks) {
            // Ensure that the keys are the same
            require(newGovKey == _getGovernor() && newCommKey == _getCommunityKey());

            Key memory newAggKey = keyManager.getAggregateKey();
            Key memory currentAggKey = getKeyManager().getAggregateKey();

            require(
                newAggKey.pubKeyX == currentAggKey.pubKeyX && newAggKey.pubKeyYParity == currentAggKey.pubKeyYParity
            );

            // Ensure that the last validate time is not in the future
            require(lastValidateTime <= block.timestamp);
        } else {
            // Check that the addresses have been initialized
            require(newGovKey != address(0) && newCommKey != address(0));
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Transfer and Fetch                      //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Can do a combination of all fcns in this contract. It first fetches all
     *          deposits , then it performs all transfers specified with the rest
     *          of the inputs, the same as transferBatch (where all inputs are again required
     *          to be of equal length - however the lengths of the fetch inputs do not have to
     *          be equal to lengths of the transfer inputs). Fetches/transfers of native are
     *          indicated with 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE as the token address.
     * @dev     FetchAndDeploy is executed first to handle the edge case , which probably shouldn't
     *          happen anyway, where a deploy and a fetch for the same address are in the same batch.
     *          Transfers are executed last to ensure that all fetching has been completed first.
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param deployFetchParamsArray    The array of deploy and fetch parameters
     * @param fetchParamsArray    The array of fetch parameters
     * @param transferParamsArray The array of transfer parameters
     */
    function allBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray,
        FetchParams[] calldata fetchParamsArray,
        TransferParams[] calldata transferParamsArray
    )
        external
        override
        onlyNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(abi.encode(this.allBatch.selector, deployFetchParamsArray, fetchParamsArray, transferParamsArray))
        )
    {
        // Fetch by deploying new deposits
        _deployAndFetchBatch(deployFetchParamsArray);

        // Fetch from already deployed deposits
        _fetchBatch(fetchParamsArray);

        // Send all transfers
        _transferBatch(transferParamsArray);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Transfers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Transfers native or a token from this vault to a recipient
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param transferParams       The transfer parameters
     */
    function transfer(
        SigData calldata sigData,
        TransferParams calldata transferParams
    )
        external
        override
        onlyNotSuspended
        nzAddr(transferParams.token)
        nzAddr(transferParams.recipient)
        nzUint(transferParams.amount)
        consumesKeyNonce(sigData, keccak256(abi.encode(this.transfer.selector, transferParams)))
    {
        _transfer(transferParams.token, transferParams.recipient, transferParams.amount);
    }

    /**
     * @notice  Transfers native or tokens from this vault to recipients.
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param transferParamsArray The array of transfer parameters.
     */
    function transferBatch(
        SigData calldata sigData,
        TransferParams[] calldata transferParamsArray
    )
        external
        override
        onlyNotSuspended
        consumesKeyNonce(sigData, keccak256(abi.encode(this.transferBatch.selector, transferParamsArray)))
    {
        _transferBatch(transferParamsArray);
    }

    /**
     * @notice  Transfers native or tokens from this vault to recipients.
     * @param transferParamsArray The array of transfer parameters.
     */
    function _transferBatch(TransferParams[] calldata transferParamsArray) private {
        uint256 length = transferParamsArray.length;
        for (uint256 i = 0; i < length; ) {
            _transfer(transferParamsArray[i].token, transferParamsArray[i].recipient, transferParamsArray[i].amount);
            unchecked {
                ++i;
            }
        }
    }

    /**
     * @notice  Transfers ETH or a token from this vault to a recipient
     * @dev     When transfering native tokens, using call function limiting the amount of gas so
     *          the receivers can't consume all the gas. Setting that amount of gas to more than
     *          2300 to future-proof the contract in case of opcode gas costs changing.
     * @dev     When transferring ERC20 tokens, if it fails ensure the transfer fails gracefully
     *          to not revert an entire batch. e.g. usdc blacklisted recipient. Following safeTransfer
     *          approach to support tokens that don't return a bool.
     * @param token The address of the token to be transferred
     * @param recipient The address of the recipient of the transfer
     * @param amount    The amount to transfer, in wei (uint)
     */
    function _transfer(address token, address payable recipient, uint256 amount) private {
        if (address(token) == _NATIVE_ADDR) {
            // solhint-disable-next-line avoid-low-level-calls
            (bool success, ) = recipient.call{gas: _GAS_TO_FORWARD, value: amount}("");
            if (!success) {
                emit TransferNativeFailed(recipient, amount);
            }
        } else {
            // solhint-disable-next-line avoid-low-level-calls
            (bool success, bytes memory returndata) = token.call(
                abi.encodeWithSelector(IERC20(token).transfer.selector, recipient, amount)
            );

            // No need to check token.code.length since it comes from a gated call
            bool transferred = success && (returndata.length == uint256(0) || abi.decode(returndata, (bool)));
            if (!transferred) emit TransferTokenFailed(recipient, amount, token, returndata);
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Fetch Deposits                    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Retrieves any token from multiple address, deterministically generated using
     *          create2, by creating a contract for that address, sending it to this vault.
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param deployFetchParamsArray    The array of deploy and fetch parameters
     */
    function deployAndFetchBatch(
        SigData calldata sigData,
        DeployFetchParams[] calldata deployFetchParamsArray
    )
        external
        override
        onlyNotSuspended
        consumesKeyNonce(sigData, keccak256(abi.encode(this.deployAndFetchBatch.selector, deployFetchParamsArray)))
    {
        _deployAndFetchBatch(deployFetchParamsArray);
    }

    function _deployAndFetchBatch(DeployFetchParams[] calldata deployFetchParamsArray) private {
        // Deploy deposit contracts
        uint256 length = deployFetchParamsArray.length;
        for (uint256 i = 0; i < length; ) {
            new Deposit{salt: deployFetchParamsArray[i].swapID}(IERC20Lite(deployFetchParamsArray[i].token));
            unchecked {
                ++i;
            }
        }
    }

    /**
     * @notice  Retrieves any token addresses where a Deposit contract is already deployed.
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param fetchParamsArray    The array of fetch parameters
     */
    function fetchBatch(
        SigData calldata sigData,
        FetchParams[] calldata fetchParamsArray
    )
        external
        override
        onlyNotSuspended
        consumesKeyNonce(sigData, keccak256(abi.encode(this.fetchBatch.selector, fetchParamsArray)))
    {
        _fetchBatch(fetchParamsArray);
    }

    /**
     * @notice  Retrieves any token from multiple addresses where a Deposit contract is already deployed.
     *          It emits an event if the fetch fails.
     * @param fetchParamsArray    The array of fetch parameters
     */
    function _fetchBatch(FetchParams[] calldata fetchParamsArray) private {
        uint256 length = fetchParamsArray.length;
        for (uint256 i = 0; i < length; ) {
            Deposit(fetchParamsArray[i].fetchContract).fetch(IERC20Lite(fetchParamsArray[i].token));
            unchecked {
                ++i;
            }
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //         Initiate cross-chain swaps (source chain)        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Swaps native token for a token in another chain. The egress token will be transferred to the specified
     *          destination address on the destination chain.
     * @dev     Checking the validity of inputs shall be done as part of the event witnessing. Only the amount is checked
     *          to explicity indicate that an amount is required.  It isn't preventing spamming.
     * @param dstChain      The destination chain according to the Chainflip Protocol's nomenclature.
     * @param dstAddress    Bytes containing the destination address on the destination chain.
     * @param dstToken      Destination token to be swapped to.
     * @param cfParameters  Additional paramters to be passed to the Chainflip protocol.
     */
    function xSwapNative(
        uint32 dstChain,
        bytes memory dstAddress,
        uint32 dstToken,
        bytes calldata cfParameters
    ) external payable override onlyNotSuspended nzUint(msg.value) {
        emit SwapNative(dstChain, dstAddress, dstToken, msg.value, msg.sender, cfParameters);
    }

    /**
     * @notice  Swaps ERC20 token for a token in another chain. The desired token will be transferred to the specified
     *          destination address on the destination chain. The provided ERC20 token must be supported by the Chainflip Protocol.
     * @dev     Checking the validity of inputs shall be done as part of the event witnessing. Only the amount is checked
     *          to explicity indicate that an amount is required.
     * @param dstChain      The destination chain according to the Chainflip Protocol's nomenclature.
     * @param dstAddress    Bytes containing the destination address on the destination chain.
     * @param dstToken      Uint containing the specifics of the swap to be performed according to Chainflip's nomenclature.
     * @param srcToken      Address of the source token to swap.
     * @param amount        Amount of tokens to swap.
     * @param cfParameters  Additional paramters to be passed to the Chainflip protocol.
     */
    function xSwapToken(
        uint32 dstChain,
        bytes memory dstAddress,
        uint32 dstToken,
        IERC20 srcToken,
        uint256 amount,
        bytes calldata cfParameters
    ) external override onlyNotSuspended nzUint(amount) {
        srcToken.safeTransferFrom(msg.sender, address(this), amount);
        emit SwapToken(dstChain, dstAddress, dstToken, address(srcToken), amount, msg.sender, cfParameters);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //     Initiate cross-chain call and swap (source chain)    //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Performs a cross-chain call to the destination address on the destination chain. Native tokens must be paid
     *          to this contract. The swap intent determines if the provided tokens should be swapped to a different token
     *          and transferred as part of the cross-chain call. Otherwise, all tokens are used as a payment for gas on the destination chain.
     *          The message parameter is transmitted to the destination chain as part of the cross-chain call.
     * @dev     Checking the validity of inputs shall be done as part of the event witnessing. Only the amount is checked
     *          to explicity inidcate that an amount is required. It isn't preventing spamming.
     *
     * @param dstChain      The destination chain according to the Chainflip Protocol's nomenclature.
     * @param dstAddress    Bytes containing the destination address on the destination chain.
     * @param dstToken      Uint containing the specifics of the swap to be performed, if any, as part of the xCall. The string
     *                      must follow Chainflip's nomenclature. It can signal that no swap needs to take place
     *                      and the source token will be used for gas in a swapless xCall.
     * @param message       The message to be sent to the egress chain. This is a general purpose message.
     * @param gasAmount     The amount to be used for gas in the egress chain.
     * @param cfParameters  Additional paramters to be passed to the Chainflip protocol.
     */
    function xCallNative(
        uint32 dstChain,
        bytes calldata dstAddress,
        uint32 dstToken,
        bytes calldata message,
        uint256 gasAmount,
        bytes calldata cfParameters
    ) external payable override onlyNotSuspended nzUint(msg.value) {
        emit XCallNative(dstChain, dstAddress, dstToken, msg.value, msg.sender, message, gasAmount, cfParameters);
    }

    /**
     * @notice  Performs a cross-chain call to the destination chain and destination address. An ERC20 token amount
     *          needs to be approved to this contract. The ERC20 token must be supported by the Chainflip Protocol.
     *          The swap intent determines whether the provided tokens should be swapped to a different token
     *          by the Chainflip Protocol. If so, the swapped tokens will be transferred to the destination chain as part
     *          of the cross-chain call. Otherwise, the tokens are used as a payment for gas on the destination chain.
     *          The message parameter is transmitted to the destination chain as part of the cross-chain call.
     * @dev     Checking the validity of inputs shall be done as part of the event witnessing. Only the amount is checked
     *          to explicity indicate that an amount is required.
     * @param dstChain      The destination chain according to the Chainflip Protocol's nomenclature.
     * @param dstAddress    Bytes containing the destination address on the destination chain.
     * @param dstToken      Uint containing the specifics of the swap to be performed, if any, as part of the xCall. The string
     *                      must follow Chainflip's nomenclature. It can signal that no swap needs to take place
     *                      and the source token will be used for gas in a swapless xCall.
     * @param message       The message to be sent to the egress chain. This is a general purpose message.
     * @param gasAmount     The amount to be used for gas in the egress chain.
     * @param srcToken      Address of the source token.
     * @param amount        Amount of tokens to swap.
     * @param cfParameters  Additional paramters to be passed to the Chainflip protocol.
     */
    function xCallToken(
        uint32 dstChain,
        bytes memory dstAddress,
        uint32 dstToken,
        bytes calldata message,
        uint256 gasAmount,
        IERC20 srcToken,
        uint256 amount,
        bytes calldata cfParameters
    ) external override onlyNotSuspended nzUint(amount) {
        srcToken.safeTransferFrom(msg.sender, address(this), amount);
        emit XCallToken(
            dstChain,
            dstAddress,
            dstToken,
            address(srcToken),
            amount,
            msg.sender,
            message,
            gasAmount,
            cfParameters
        );
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                     Gas topups                           //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Add gas (topup) to an existing cross-chain call with the unique identifier swapID.
     *          Native tokens must be paid to this contract as part of the call.
     * @param swapID    The unique identifier for this swap (bytes32)
     */
    function addGasNative(bytes32 swapID) external payable override onlyNotSuspended nzUint(msg.value) {
        emit AddGasNative(swapID, msg.value);
    }

    /**
     * @notice  Add gas (topup) to an existing cross-chain call with the unique identifier swapID.
     *          A Chainflip supported token must be paid to this contract as part of the call.
     * @param swapID    The unique identifier for this swap (bytes32)
     * @param token     Address of the token to provide.
     * @param amount    Amount of tokens to provide.
     */
    function addGasToken(
        bytes32 swapID,
        uint256 amount,
        IERC20 token
    ) external override onlyNotSuspended nzUint(amount) {
        token.safeTransferFrom(msg.sender, address(this), amount);
        emit AddGasToken(swapID, amount, address(token));
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //      Execute cross-chain call and swap (dest. chain)     //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Transfers native or a token from this vault to a recipient and makes a function call
     *          completing a cross-chain swap and call. The ICFReceiver interface is expected on
     *          the receiver's address. A message is passed to the receiver along with other
     *          parameters specifying the origin of the swap.
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param transferParams  The transfer parameters
     * @param srcChain        The source chain where the call originated from.
     * @param srcAddress      The address where the transfer originated within the ingress chain.
     * @param message         The message to be passed to the recipient.
     */
    function executexSwapAndCall(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    )
        external
        override
        onlyNotSuspended
        nzAddr(transferParams.token)
        nzAddr(transferParams.recipient)
        nzUint(transferParams.amount)
        consumesKeyNonce(
            sigData,
            keccak256(abi.encode(this.executexSwapAndCall.selector, transferParams, srcChain, srcAddress, message))
        )
    {
        // Logic in another internal function to avoid the stackTooDeep error
        _executexSwapAndCall(transferParams, srcChain, srcAddress, message);
    }

    /**
     * @notice Logic for transferring the tokens and calling the recipient. It's on the receiver to
     *         make sure the call doesn't revert, otherwise the tokens won't be transferred.
     *         The _transfer function is not used because we want to be able to embed the native token
     *         into the cfReceive call to avoid doing two external calls.
     *         In case of revertion the tokens will remain in the Vault. Therefore, the destination
     *         contract must ensure it doesn't revert e.g. using try-catch mechanisms.
     * @dev    In the case of the ERC20 transfer reverting, not handling the error to allow for tx replay.
     *         Also, to ensure the cfReceive call is made only if the transfer is successful.
     */
    function _executexSwapAndCall(
        TransferParams calldata transferParams,
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    ) private {
        uint256 nativeAmount;

        if (transferParams.token == _NATIVE_ADDR) {
            nativeAmount = transferParams.amount;
        } else {
            IERC20(transferParams.token).safeTransfer(transferParams.recipient, transferParams.amount);
        }

        ICFReceiver(transferParams.recipient).cfReceive{value: nativeAmount}(
            srcChain,
            srcAddress,
            message,
            transferParams.token,
            transferParams.amount
        );
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //          Execute cross-chain call (dest. chain)          //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Executes a cross-chain function call. The ICFReceiver interface is expected on
     *          the receiver's address. A message is passed to the receiver along with other
     *          parameters specifying the origin of the swap. This is used for cross-chain messaging
     *          without any swap taking place on the Chainflip Protocol.
     * @param sigData    Struct containing the signature data over the message
     *                   to verify, signed by the aggregate key.
     * @param srcChain       The source chain where the call originated from.
     * @param srcAddress     The address where the transfer originated from in the ingressParams.
     * @param message        The message to be passed to the recipient.
     */
    function executexCall(
        SigData calldata sigData,
        address recipient,
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    )
        external
        override
        onlyNotSuspended
        nzAddr(recipient)
        consumesKeyNonce(
            sigData,
            keccak256(abi.encode(this.executexCall.selector, recipient, srcChain, srcAddress, message))
        )
    {
        ICFReceiver(recipient).cfReceivexCall(srcChain, srcAddress, message);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                 Auxiliary chain actions                  //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Transfer funds and pass calldata to be executed on a Multicall contract.
     * @dev     For safety purposes it's preferred to execute calldata externally with
     *          a limited amount of funds instead of executing arbitrary calldata here.
     * @dev     Calls are not reverted upon Multicall.run() failure so the nonce gets consumed. The 
     *          gasMulticall parameters is needed to prevent an insufficient gas griefing attack. 
     * @param sigData         Struct containing the signature data over the message
     *                        to verify, signed by the aggregate key.
     * @param transferParams  The transfer parameters inluding the token and amount to be transferred
     *                        and the multicall contract address.
     * @param calls           Array of actions to be executed.
     * @param gasMulticall    Gas that must be forwarded to the multicall.

     */
    function executeActions(
        SigData calldata sigData,
        TransferParams calldata transferParams,
        IMulticall.Call[] calldata calls,
        uint256 gasMulticall
    )
        external
        override
        onlyNotSuspended
        consumesKeyNonce(
            sigData,
            keccak256(abi.encode(this.executeActions.selector, transferParams, calls, gasMulticall))
        )
    {
        // Fund and run multicall
        uint256 valueToSend;

        if (transferParams.amount > 0) {
            if (transferParams.token == _NATIVE_ADDR) {
                valueToSend = transferParams.amount;
            } else {
                IERC20(transferParams.token).approve(transferParams.recipient, transferParams.amount);
            }
        }

        // solhint-disable-next-line avoid-low-level-calls
        (bool success, bytes memory reason) = transferParams.recipient.call{gas: gasMulticall, value: valueToSend}(
            abi.encodeWithSelector(IMulticall.run.selector, calls, transferParams.token, transferParams.amount)
        );

        if (!success) {
            // Validate that the relayer has sent enough gas for the call.
            // See https://ronan.eth.limo/blog/ethereum-gas-dangers/
            if (gasleft() <= gasMulticall / 63) {
                // Emulate an out of gas exception by explicitly trigger invalid opcode to consume all gas and
                // bubble-up the effects, since neither revert or assert consume all gas since Solidity 0.8.0.

                // solhint-disable no-inline-assembly
                /// @solidity memory-safe-assembly
                assembly {
                    invalid()
                }
                // solhint-enable no-inline-assembly
            }
            if (transferParams.amount > 0 && transferParams.token != _NATIVE_ADDR) {
                IERC20(transferParams.token).approve(transferParams.recipient, 0);
            }
            emit ExecuteActionsFailed(transferParams.recipient, transferParams.amount, transferParams.token, reason);
        } else {
            require(transferParams.recipient.code.length > 0);
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Governance                        //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice Withdraw all funds to governance address in case of emergency. This withdrawal needs
     *         to be approved by the Community and it can only be executed if no nonce from the
     *         current AggKey had been consumed in _AGG_KEY_TIMEOUT time. It is a last resort and
     *         can be used to rectify an emergency.
     * @param tokens    The addresses of the tokens to be transferred
     */
    function govWithdraw(
        address[] calldata tokens
    ) external override onlyGovernor onlyCommunityGuardDisabled onlySuspended timeoutEmergency {
        // Could use msg.sender or getGovernor() but hardcoding the get call just for extra safety
        address payable recipient = payable(getKeyManager().getGovernanceKey());

        // Transfer all native and ERC20 Tokens
        for (uint256 i = 0; i < tokens.length; i++) {
            if (tokens[i] == _NATIVE_ADDR) {
                _transfer(_NATIVE_ADDR, recipient, address(this).balance);
            } else {
                _transfer(tokens[i], recipient, IERC20(tokens[i]).balanceOf(address(this)));
            }
        }
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Check that no nonce has been consumed in the last 3 days - emergency
    modifier timeoutEmergency() {
        require(
            block.timestamp - getKeyManager().getLastValidateTime() >= _AGG_KEY_EMERGENCY_TIMEOUT,
            "Vault: not enough time"
        );
        _;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Fallbacks                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev For receiving native when Deposit.fetch() is called.
    receive() external payable {}
}

contract FLIP is ERC20, IFLIP, Shared {
    address private issuer;

    constructor(
        uint256 flipTotalSupply,
        uint256 numGenesisValidators,
        uint256 genesisStake,
        address receiverGenesisValidatorFlip, // StateChainGateway
        address receiverGenesisFlip,
        address genesisIssuer //StateChainGateway
    )
        ERC20("Chainflip", "FLIP")
        nzAddr(receiverGenesisValidatorFlip)
        nzAddr(receiverGenesisFlip)
        nzUint(flipTotalSupply)
        nzAddr(genesisIssuer)
    {
        uint256 genesisValidatorFlip = numGenesisValidators * genesisStake;
        _mint(receiverGenesisValidatorFlip, genesisValidatorFlip);
        _mint(receiverGenesisFlip, flipTotalSupply - genesisValidatorFlip);
        issuer = genesisIssuer;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  State-changing functions                //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice Mint FLIP tokens to an account. This is controlled via an issuer
     *         controlled by the StateChain to adjust the supply of FLIP tokens.
     * @dev    The _mint function checks for zero address. We do not check for
     *         zero amount because there is no real reason to revert and we want
     *         to minimise reversion of State Chain calls
     * @param account   Account to receive the newly minted tokens
     * @param amount    Amount of tokens to mint
     */
    function mint(address account, uint amount) external override onlyIssuer {
        _mint(account, amount);
    }

    /**
     * @notice Mint FLIP tokens to an account. This is controlled via an issuer
     *         controlled by the StateChain to adjust the supply of FLIP tokens.
     * @dev    The _burn function checks for zero address. We do not check for
     *         zero amount because there is no real reason to revert and we want
     *         to minimise reversion of State Chain calls.
     * @param account   Account to burn the tokens from
     * @param amount    Amount of tokens to burn
     */
    function burn(address account, uint amount) external override onlyIssuer {
        _burn(account, amount);
    }

    /**
     * @notice Update the issuer address. This is to be controlled via an issuer
     *         controlled by the StateChain.
     * @param newIssuer   Account that can mint and burn FLIP tokens.
     */
    function updateIssuer(address newIssuer) external override nzAddr(issuer) onlyIssuer {
        emit IssuerUpdated(issuer, newIssuer);
        issuer = newIssuer;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                  Non-state-changing functions            //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev Get the issuer address.
    function getIssuer() external view override returns (address) {
        return issuer;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                        Modifiers                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev    Check that the caller is the token issuer.
    modifier onlyIssuer() {
        require(msg.sender == issuer, "FLIP: not issuer");
        _;
    }
}

contract DeployerContract is IShared {
    Vault public immutable vault;
    KeyManager public immutable keyManager;
    StateChainGateway public immutable stateChainGateway;
    FLIP public immutable flip;

    // The underlying contracts will check for non-zero inputs.
    constructor(
        Key memory aggKey,
        address govKey,
        address commKey,
        uint256 minFunding,
        uint256 initSupply,
        uint256 numGenesisValidators,
        uint256 genesisStake
    ) {
        KeyManager _keyManager = new KeyManager(aggKey, govKey, commKey);
        Vault _vault = new Vault(_keyManager);
        StateChainGateway _stateChainGateway = new StateChainGateway(_keyManager, minFunding);
        FLIP _flip = new FLIP(
            initSupply,
            numGenesisValidators,
            genesisStake,
            address(_stateChainGateway),
            govKey,
            address(_stateChainGateway)
        );
        // Set the FLIP address in the StateChainGateway contract
        _stateChainGateway.setFlip(_flip);

        // Storing all addresses for traceability.
        vault = _vault;
        keyManager = _keyManager;
        stateChainGateway = _stateChainGateway;
        flip = _flip;
    }
}

abstract contract CFReceiver is ICFReceiver {
    /// @dev The address used to indicate whether the funds received are native or a token
    address private constant _NATIVE_ADDR = 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE;

    /// @dev    Chainflip's Vault address where xSwaps and xCalls will be originated from.
    address public cfVault;
    address public owner;

    constructor(address _cfVault) {
        cfVault = _cfVault;
        owner = msg.sender;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                   CF Vault calls                         //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice  Receiver of a cross-chain swap and call made by the Chainflip Protocol.

     * @param srcChain      The source chain according to the Chainflip Protocol's nomenclature.
     * @param srcAddress    Bytes containing the source address on the source chain.
     * @param message       The message sent on the source chain. This is a general purpose message.
     * @param token         Address of the token received. _NATIVE_ADDR if native.
     * @param amount        Amount of tokens received. This will match msg.value for native tokens.
     */
    function cfReceive(
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) external payable override onlyCfVault {
        _cfReceive(srcChain, srcAddress, message, token, amount);
    }

    /**
     * @notice  Receiver of a cross-chain call made by the Chainflip Protocol.

     * @param srcChain      The source chain according to the Chainflip Protocol's nomenclature.
     * @param srcAddress    Bytes containing the source address on the source chain.
     * @param message       The message sent on the source chain. This is a general purpose message.
     */
    function cfReceivexCall(
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message
    ) external override onlyCfVault {
        _cfReceivexCall(srcChain, srcAddress, message);
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //             User's logic to be implemented               //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev Internal function to be overriden by the user's logic.
    function _cfReceive(
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal virtual;

    /// @dev Internal function to be overriden by the user's logic.
    function _cfReceivexCall(uint32 srcChain, bytes calldata srcAddress, bytes calldata message) internal virtual;

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                 Update Vault address                     //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /**
     * @notice           Update Chanflip's Vault address.
     * @param _cfVault    New Chainflip's Vault address.
     */
    function updateCfVault(address _cfVault) external onlyOwner {
        cfVault = _cfVault;
    }

    //////////////////////////////////////////////////////////////
    //                                                          //
    //                          Modifiers                       //
    //                                                          //
    //////////////////////////////////////////////////////////////

    /// @dev Check that the sender is the Chainflip's Vault.
    modifier onlyCfVault() {
        require(msg.sender == cfVault, "CFReceiver: caller not Chainflip sender");
        _;
    }

    /// @dev Check that the sender is the owner.
    modifier onlyOwner() {
        require(msg.sender == owner, "CFReceiver: caller not owner");
        _;
    }
}

contract NewTestReceiver is CFReceiver, IMulticall {
    address vault;
    address flip;
    address fund_manager;

    address[] public callTargets;
    bytes[] public callArguments;

    constructor(address _vault, address _fund_manager, address _flip) CFReceiver(_vault) {
        vault = _vault;
        fund_manager = _fund_manager;
        flip = _flip;
    }

    function _process_call_sequence() internal {
        for (uint256 i = 0; i < callTargets.length; i++) {
            callTargets[i].call(callArguments[i]);
        }
    }

    // IMulticall override
    function run(Call[] calldata calls, address token, uint256 amount) external payable {
        _process_call_sequence();
    }

    // CFReceiver overrides
    function _cfReceive(
        uint32 srcChain,
        bytes calldata srcAddress,
        bytes calldata message,
        address token,
        uint256 amount
    ) internal override {
        // Ignore all parameters, this will only call the function stack in order
        _process_call_sequence();
    }

    function _cfReceivexCall(uint32 srcChain, bytes calldata srcAddress, bytes calldata message) internal override {
        // Ignore all parameters, this will only call the function stack in order
        _process_call_sequence();
    }

    // We should add here all the unprivileged functions that can be called

    function add_flip_approve(address spender, uint256 amount) public {
        callTargets.push(flip);
        callArguments.push(abi.encodeWithSelector(ERC20.approve.selector, spender, amount));
    }

    function add_flip_transfer(address to, uint256 amount) public {
        callTargets.push(flip);
        callArguments.push(abi.encodeWithSelector(ERC20.transfer.selector, to, amount));
    }

    function add_fund_manager_fund(bytes32 id, uint256 amount, address return_addr) public {
        callTargets.push(fund_manager);
        callArguments.push(
            abi.encodeWithSelector(StateChainGateway.fundStateChainAccount.selector, id, amount, return_addr)
        );
    }

    function add_fund_manager_execute(bytes32 id) public {
        callTargets.push(fund_manager);
        callArguments.push(abi.encodeWithSelector(StateChainGateway.executeRedemption.selector, id));
    }

    function add_vault_xswaptoken(
        uint32 dstchain,
        bytes memory dstaddr,
        uint16 dsttoken,
        address srctoken,
        uint256 amount
    ) public {
        callTargets.push(vault);
        callArguments.push(
            abi.encodeWithSelector(Vault.xSwapToken.selector, dstchain, dstaddr, dsttoken, IERC20(srctoken), amount)
        );
    }
}

contract NewTestEchidna is IShared {
    // Events for debugging (can be replaced by crytic/properties helpers)
    event log_string(string);
    event log_uint(uint256);
    event log_addr(address);

    // Randomly obtained via privatekeys.pw, except the aggregate
    bytes32 internal govPK = 0xb670a09c7ecb70fe3d1616ea441f7f2f3d36ca2ad7281ae51d3a068910a2b7a1;
    address internal govKey = address(0x3421b011C6a5f7c1ED438368565A5A8943063D19);
    bytes32 internal commPK = 0xf8b408fd2e00c01ed0810614d34ed23d27b67952fd2f07267fbeec845ef24cc7;
    address internal commKey = address(0x6C377BdD40216c5b997Ab2bf0CFF8c2624F9Dd86);
    bytes32 internal aggPK = 0xfbcb47bc85b881e0dfb31c872d4e06848f80530ccbd18fc016a27c4a744d0eba;
    uint256 internal minStake = 1000 * E_18;

    // Common constants across tests
    uint256 internal constant E_18 = 10 ** 18;
    uint256 internal constant PUBKEYX = 22479114112312168431982914496826057754130808976066989807481484372215659188398;
    uint8 internal constant PUBKEYYPARITY = 1;
    uint256 internal constant INIT_SUPPLY = 9 * 10 ** 7 * E_18;
    uint256 internal constant NUM_GENESIS_VALIDATORS = 5;
    uint256 internal constant GENESIS_STAKE = 5000 * E_18;

    // Node ID and nonce
    uint256 internal nodeid = 1;
    uint256 internal nonce = 0;

    // State variables
    DeployerContract internal dc;
    Vault internal vault;
    KeyManager internal keyManager;
    StateChainGateway internal stateChainGateway;
    FLIP internal flip;
    NewTestReceiver internal receiver;
    MockToken[] internal tokens;
    mapping(uint256 => address) internal stakingAddresses;
    mapping(uint256 => uint256) internal redemptionedAmounts;
    mapping(uint256 => bool) internal redemptionableNodeID;

    // Echidna requires that no parameters are passed to the constructor so we need to set
    // constants for the deployments of the contracts
    constructor() {
        dc = new DeployerContract(
            Key(PUBKEYX, PUBKEYYPARITY),
            govKey,
            commKey,
            minStake,
            INIT_SUPPLY,
            NUM_GENESIS_VALIDATORS,
            GENESIS_STAKE
        );

        // Local references to contracts
        vault = dc.vault();
        keyManager = dc.keyManager();
        stateChainGateway = dc.stateChainGateway();
        flip = dc.flip();

        // Mock tokens (can be extended to any size)
        tokens.push(new MockToken("One token", "OTK"));
        tokens.push(new MockToken("Yet another token", "YAT"));

        // Receiver contract to test vault calls
        hevm.prank(govKey);
        receiver = new NewTestReceiver(address(vault), address(stateChainGateway), address(flip));
    }

    // ===============================================================================================
    //                                       Helpers
    // ===============================================================================================

    function generate_new_aggregate_key() internal returns (Key memory k, bytes32 priv_key) {
        string[] memory inp = new string[](2);
        inp[0] = "python3";
        inp[1] = "tests/keygen.py";

        bytes memory res = hevm.ffi(inp);
        (uint256 priv, uint256 pubKeyX, uint8 pubKeyYParity) = abi.decode(res, (uint256, uint256, uint8));
        k.pubKeyX = pubKeyX;
        k.pubKeyYParity = pubKeyYParity;
        priv_key = bytes32(priv);
    }

    function generate_new_keymanager() internal returns (KeyManager km, bytes32 priv_key) {
        Key memory newagg;

        (newagg, priv_key) = generate_new_aggregate_key();

        km = new KeyManager(newagg, govKey, commKey);
    }

    function sign_message_with_key(
        bytes32 message,
        uint256 sigNonce,
        bytes32 key,
        address sender,
        address cont
    ) internal returns (SigData memory out) {
        out.nonce = sigNonce;

        bytes32 msgHash = keccak256(abi.encode(message, sigNonce, sender, block.chainid, cont));

        string[] memory inp = new string[](5);
        inp[0] = "python3";
        inp[1] = "tests/signer.py";
        inp[2] = bytesToString(bytes.concat(msgHash));
        inp[3] = bytesToString(bytes.concat(key));
        inp[4] = toString(sigNonce);

        bytes memory res = hevm.ffi(inp);
        (uint256 signed, address ktimesg) = abi.decode(res, (uint256, address));

        out.sig = signed;
        out.kTimesGAddress = ktimesg;
    }

    function test_get_tokens_from_gov(uint256 amount) public {
        hevm.prank(govKey);
        flip.transfer(msg.sender, amount);

        hevm.prank(msg.sender);
        flip.approve(address(stateChainGateway), type(uint256).max);

        hevm.prank(msg.sender);
        flip.approve(address(vault), type(uint256).max);
    }

    // ===============================================================================================
    //                    Wrappers for functions needing signatures in KeyManager
    // ===============================================================================================

    // The sender field for signatures here is always address(keyManager)
    function test_set_agg_key_with_agg_key(Key calldata newkey) public {
        bytes32 message = keccak256(abi.encode(keyManager.setAggKeyWithAggKey.selector, newkey));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(keyManager), address(keyManager));
        nonce++;

        keyManager.setAggKeyWithAggKey(sig, newkey);

        assert(keccak256(abi.encode(newkey)) == keccak256(abi.encode(keyManager.getAggregateKey())));
    }

    function test_set_gov_key_with_agg_key(address newkey) public {
        bytes32 message = keccak256(abi.encode(keyManager.setGovKeyWithAggKey.selector, newkey));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(keyManager), address(keyManager));
        nonce++;

        keyManager.setGovKeyWithAggKey(sig, newkey);

        assert(newkey == keyManager.getGovernanceKey());
    }

    function test_set_comm_key_with_agg_key(address newkey) public {
        bytes32 message = keccak256(abi.encode(keyManager.setCommKeyWithAggKey.selector, newkey));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(keyManager), address(keyManager));
        nonce++;

        keyManager.setCommKeyWithAggKey(sig, newkey);

        assert(newkey == keyManager.getCommunityKey());
    }

    // ===============================================================================================
    //                 Wrappers for functions needing signatures in StateChainGateway
    // ===============================================================================================

    // this will need some sanity check on the values (can we interact with the sc from echidna?)
    function test_update_flip_supply(uint256 new_supply, uint256 sc_blocknumber) public {
        bytes32 message = keccak256(
            abi.encode(stateChainGateway.updateFlipSupply.selector, new_supply, sc_blocknumber)
        );

        SigData memory sig = sign_message_with_key(
            message,
            nonce,
            aggPK,
            address(stateChainGateway),
            address(keyManager)
        );
        nonce++;

        uint256 flip_supply = flip.totalSupply();
        uint256 prev_balance = flip.balanceOf(address(stateChainGateway));
        bool increased = new_supply > flip_supply;

        stateChainGateway.updateFlipSupply(sig, new_supply, sc_blocknumber);

        if (increased) {
            uint256 difference = new_supply - flip_supply;
            assert(flip.balanceOf(address(stateChainGateway)) == prev_balance + difference);
        } else {
            uint256 difference = flip_supply - new_supply;
            assert(flip.balanceOf(address(stateChainGateway)) == prev_balance - difference);
        }
    }

    // does not check that the argument is indeed a key manager
    function test_update_stateChainGateway_key_manager(address newkeyman) internal {
        bytes32 message = keccak256(abi.encode(stateChainGateway.updateKeyManager.selector, newkeyman));

        SigData memory sig = sign_message_with_key(
            message,
            nonce,
            aggPK,
            address(stateChainGateway),
            address(keyManager)
        );
        nonce++;

        stateChainGateway.updateKeyManager(sig, IKeyManager(newkeyman), false);

        assert(newkeyman == address(stateChainGateway.getKeyManager()));
    }

    // Token staking test
    function test_fund(uint256 amount) public {
        hevm.prank(msg.sender);
        stateChainGateway.fundStateChainAccount(bytes32(nodeid), amount);
        stakingAddresses[nodeid] = msg.sender;
        redemptionableNodeID[nodeid] = true;

        nodeid++;
    }

    // funder will be msg.sender for now
    function test_register_redemption(uint256 node, uint256 amount, uint48 expiryTime) public {
        uint256 nodeID = 1 + (node % (nodeid - 1));
        address funder = msg.sender;

        require(redemptionableNodeID[nodeID] == true);

        bytes32 message = keccak256(
            abi.encode(stateChainGateway.registerRedemption.selector, nodeID, amount, funder, expiryTime)
        );

        SigData memory sig = sign_message_with_key(
            message,
            nonce,
            aggPK,
            address(stateChainGateway),
            address(keyManager)
        );
        nonce++;

        stateChainGateway.registerRedemption(sig, bytes32(nodeID), amount, funder, expiryTime);
        StateChainGateway.Redemption memory result = stateChainGateway.getPendingRedemption(bytes32(nodeID));

        redemptionedAmounts[nodeID] = amount;

        assert(result.redeemAddress == stakingAddresses[nodeID]);
    }

    function test_execute_redemption(uint256 node) public {
        uint256 nodeID = 1 + (node % (nodeid - 1));
        uint256 balance_before = flip.balanceOf(stakingAddresses[nodeID]);

        // Execute the redemption
        stateChainGateway.executeRedemption(bytes32(nodeID));

        // Make sure the redemption was fulfilled
        assert(flip.balanceOf(stakingAddresses[nodeID]) == balance_before + redemptionedAmounts[nodeID]);

        redemptionableNodeID[nodeID] = false;
    }

    function test_update_flip_issuer(address new_issuer) public {
        require(new_issuer != address(0));
        bytes32 message = keccak256(abi.encode(stateChainGateway.updateFlipIssuer.selector, new_issuer));

        SigData memory sig = sign_message_with_key(
            message,
            nonce,
            aggPK,
            address(stateChainGateway),
            address(keyManager)
        );
        nonce++;

        stateChainGateway.updateFlipIssuer(sig, new_issuer, false);

        assert(flip.getIssuer() == new_issuer);
    }

    // ===============================================================================================
    //                 Wrappers for functions needing signatures in Vault
    // ===============================================================================================

    // does not check that the argument is indeed a key manager
    function test_update_vault_key_manager(address newkeyman) internal {
        bytes32 message = keccak256(abi.encode(vault.updateKeyManager.selector, newkeyman));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.updateKeyManager(sig, IKeyManager(newkeyman), false);

        assert(newkeyman == address(vault.getKeyManager()));
    }

    // this doesn't perform any check after executing, can be used to test reentrancy
    function test_execute_xswap_and_call(
        uint8 token,
        uint256 amount,
        uint32 src_chain,
        bytes calldata src_addr,
        bytes calldata mess
    ) public {
        MockToken token_addr = tokens[token % tokens.length];

        TransferParams memory t_params;
        t_params.token = address(token_addr);
        t_params.recipient = payable(address(receiver));
        t_params.amount = amount;

        hevm.prank(address(this));
        token_addr.mint(address(vault), amount);

        bytes32 message = keccak256(
            abi.encode(vault.executexSwapAndCall.selector, t_params, src_chain, src_addr, mess)
        );

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.executexSwapAndCall(sig, t_params, src_chain, src_addr, mess);
    }

    function test_execute_xcall(uint32 srcChain, bytes calldata srcAddress, bytes calldata mess) public {
        address recipient = address(receiver);

        bytes32 message = keccak256(abi.encode(vault.executexCall.selector, recipient, srcChain, srcAddress, mess));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.executexCall(sig, recipient, srcChain, srcAddress, mess);
    }

    function test_execute_actions(uint8 token, uint256 amount, IMulticall.Call[] calldata calls) public {
        MockToken token_addr = tokens[token % tokens.length];
        address multicall_addr = address(receiver);

        // TODO: Add gas amount to the fuzzing
        uint256 gasMulticall = 100000;

        hevm.prank(address(this));
        token_addr.mint(address(vault), amount);

        TransferParams memory t_params = TransferParams(address(token_addr), payable(multicall_addr), amount);

        bytes32 message = keccak256(abi.encode(vault.executeActions.selector, t_params, calls, gasMulticall));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.executeActions(sig, t_params, calls, gasMulticall);
    }

    function test_vault_transfer(TransferParams calldata t_params) public {
        bytes32 message = keccak256(abi.encode(vault.transfer.selector, t_params));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.transfer(sig, t_params);
    }

    function test_vault_transfer_batch(TransferParams[] calldata t_params) public {
        bytes32 message = keccak256(abi.encode(vault.transferBatch.selector, t_params));

        SigData memory sig = sign_message_with_key(message, nonce, aggPK, address(vault), address(keyManager));
        nonce++;

        vault.transferBatch(sig, t_params);
    }

    // ===============================================================================================
    //           Wrappers for simplifying testing of transactions needing specific values
    // ===============================================================================================

    function test_create_new_keymanager_and_update_all() public {
        (KeyManager km, bytes32 pk) = generate_new_keymanager();

        test_update_vault_key_manager(address(km));
        test_update_stateChainGateway_key_manager(address(km));

        aggPK = pk;
        keyManager = km;
    }

    function test_fund_plus_redemption(uint256 amount) public {
        // Get a valid random amount between 10**19 and 10**19 + 10**30 - 1
        uint256 to_fund = 10 ** 19 + (amount % 10 ** 30);

        // Get tokens from governance
        hevm.prank(govKey);
        flip.transfer(msg.sender, amount);

        hevm.prank(msg.sender);
        flip.approve(address(stateChainGateway), type(uint256).max);

        hevm.prank(msg.sender);
        flip.approve(address(vault), type(uint256).max);

        hevm.prank(msg.sender);
        test_fund(to_fund);

        hevm.prank(govKey);
        test_register_redemption(nodeid - 1, to_fund, uint48(block.timestamp + 3 days));

        hevm.warp(block.timestamp + 2 days + 500);

        hevm.prank(msg.sender);
        test_execute_redemption(nodeid - 1);
    }

    function test_stateChainGateway_gov_withdrawal() public {
        hevm.prank(commKey);
        stateChainGateway.disableCommunityGuard();

        hevm.prank(govKey);
        stateChainGateway.suspend();

        hevm.prank(govKey);
        stateChainGateway.govWithdraw();
    }

    function test_vault_gov_withdrawal() public {
        address[] memory token_list = new address[](tokens.length);

        for (uint256 i = 0; i < tokens.length; i++) {
            token_list[i] = address(tokens[i]);
        }

        hevm.prank(commKey);
        stateChainGateway.disableCommunityGuard();

        hevm.prank(govKey);
        stateChainGateway.suspend();

        hevm.warp(block.timestamp + 14 days + 1);

        hevm.prank(govKey);
        vault.govWithdraw(token_list);
    }

    // ===============================================================================================
    //                                    Invariants
    // ===============================================================================================

    // Flip address in StateChainGateway must not change
    function test_constant_flip() external {
        assert(address(stateChainGateway.getFLIP()) == address(flip));
    }

    // All keymanager references must be the same
    function test_keymanager_consistency() external {
        assert(stateChainGateway.getKeyManager() == vault.getKeyManager());
    }

    // All govKey references must be the same
    function test_govkey_consistency() external {
        assert(stateChainGateway.getGovernor() == vault.getGovernor());
        assert(vault.getGovernor() == keyManager.getGovernanceKey());
    }

    // All commKey references must be the same
    function test_commkey_consistency() external {
        assert(stateChainGateway.getCommunityKey() == vault.getCommunityKey());
        assert(vault.getCommunityKey() == keyManager.getCommunityKey());
    }
}
