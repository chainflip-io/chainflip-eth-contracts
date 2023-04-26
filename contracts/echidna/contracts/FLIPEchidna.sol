pragma solidity ^0.8.0;

import "../../interfaces/IShared.sol";
import "../../interfaces/IFLIP.sol";

contract FLIPEchidna is IShared {
    IFLIP public f;

    // Expose FLIP functions to Echidna  - making them virtual to override them in tests when needed

    function mint(address account, uint amount) external virtual {
        f.mint(account, amount);
    }

    function burn(address account, uint amount) external virtual {
        f.burn(account, amount);
    }

    function updateIssuer(address newIssuer) external virtual {
        f.updateIssuer(newIssuer);
    }
}
