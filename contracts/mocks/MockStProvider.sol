// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

interface IMinter {
    function mint(address to, uint256 amount) external returns (bool);
}

interface IBurner {
    function burn(address to, uint256 amount) external returns (uint256);
}

interface IAggregator {
    function stakeAggregate(
        uint256 amountTotal,
        uint256 amountSwap,
        uint256 minimumAmountSwapOut
    ) external returns (uint256);

    function unstakeAggregate(
        uint256 amountInstantBurn,
        uint256 amountBurn,
        uint256 amountSwap,
        uint256 minimumAmountSwapOut
    ) external returns (uint256);
}

contract Minter is IMinter {
    stFLIP public stflip;
    IERC20 public flip;
    address public output;

    constructor(address _stflip, address _flip, address _output) {
        stflip = stFLIP(_stflip);
        flip = IERC20(_flip);
        output = address(_output);
    }

    function mint(address to, uint256 amount) external returns (bool) {
        // require(stflip.minter() == address(this), "this is not a valid mint contract");
        flip.transferFrom(msg.sender, output, amount);

        _mint(to, amount);
        return true;
    }

    function _mint(address to, uint256 amount) internal {
        stflip.mint(to, amount);
        // emit Mint(to, amount);
    }

    function cheatMint(address to, uint256 amount) public {
        _mint(to, amount);
    }
}

contract Burner is IBurner {
    stFLIP public stflip;
    IERC20 public flip;

    struct Burn {
        address user;
        uint256 amount;
        bool completed;
    }
    Burn[] public burns;

    constructor(address _stflip, address _flip) {
        stflip = stFLIP(_stflip);
        flip = IERC20(_flip);
    }

    // NOTE: Burn & Redeem functions are simplified for the sake of testing
    function burn(address to, uint256 amount) external returns (uint256) {
        stflip.transferFrom(msg.sender, address(this), amount);

        burns.push(Burn(to, amount, false));
        stflip.burn(amount, address(this));

        return burns.length - 1;
    }

    function redeem(uint256 burnId) external {
        require(burns[burnId].completed == false, "completed"); // Audit: Cache the burns[Burnid]

        burns[burnId].completed = true;
        flip.transfer(burns[burnId].user, burns[burnId].amount);
    }

    function cheatBurn(address to, uint256 amount) public {
        flip.transfer(to, amount);
    }
}

// solhint-disable-next-line contract-name-camelcase
contract stFLIP is ERC20 {
    address public minter;
    address public burner;

    event Burn(address from, uint256 amount, address refundee);

    constructor() ERC20("StakedFLIP", "stFLIP") {}

    function initialize(address _minter, address _burner) public {
        require(minter == address(0) && burner == address(0), "already initialized");
        minter = _minter;
        burner = _burner;
    }

    function mint(address to, uint256 amount) public {
        require(msg.sender == minter, "only minter can mint");
        _mint(to, amount);
    }

    function burn(uint256 value, address refundee) public {
        require(msg.sender == burner, "only burner can burn");
        emit Burn(msg.sender, value, refundee);
        _burn(msg.sender, value);
    }
}

contract Aggregator is IAggregator {
    address public minter;
    address public burner;

    // if positive then stFLIP is at a discount. 10**18 = 1.0x
    uint256 public mockAggregateMultiplier;
    IERC20 flip;
    stFLIP stflip;

    constructor(address _minter, address _burner, address _stflip, address _flip) {
        minter = _minter;
        burner = _burner;
        stflip = stFLIP(_stflip);
        flip = IERC20(_flip);
    }

    function stakeAggregate(
        uint256 amountTotal,
        uint256 amountSwap,
        uint256 minimumAmountSwapOut
    ) external returns (uint256) {
        flip.transferFrom(msg.sender, address(this), amountTotal);
        uint256 swapReceived;
        uint256 mintAmount = amountTotal - amountSwap;

        if (amountSwap > 0) {
            swapReceived = (amountSwap * mockAggregateMultiplier) / 10 ** 18;
            Minter(minter).cheatMint(msg.sender, swapReceived);
            flip.transfer(burner, amountSwap);
        }

        if (mintAmount > 0) {
            Minter(minter).mint(msg.sender, mintAmount);
        }

        return mintAmount + swapReceived;
    }

    function unstakeAggregate(
        uint256 amountInstantBurn,
        uint256 amountBurn,
        uint256 amountSwap,
        uint256 minimumAmountSwapOut
    ) external returns (uint256) {
        uint256 total = amountInstantBurn + amountBurn + amountSwap;
        uint256 swapReceived;

        stflip.transferFrom(msg.sender, address(this), total);

        if (amountInstantBurn > 0) {
            uint256 instantBurnId = Burner(burner).burn(msg.sender, amountInstantBurn);
            Burner(burner).redeem(instantBurnId);
        }

        if (amountBurn > 0) {
            Burner(burner).burn(msg.sender, amountBurn);
        }

        if (amountSwap > 0) {
            swapReceived = (amountSwap * (2 * 10 ** 18 - mockAggregateMultiplier)) / 10 ** 18;
            Burner(burner).cheatBurn(msg.sender, swapReceived);
        }

        return amountInstantBurn + swapReceived;
    }

    function setMockMultiplier(uint256 multiplier) public {
        mockAggregateMultiplier = multiplier;
    }
}
