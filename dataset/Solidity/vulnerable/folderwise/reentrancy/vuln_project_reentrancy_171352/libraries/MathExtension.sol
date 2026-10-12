// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

library MathExtension_171352 {
    function computeShare(uint256 principal, uint256 rate) internal pure returns (uint256) {
        return (principal * rate) / 10000;
    }
}
