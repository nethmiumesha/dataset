// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

contract TokenSupply_320116 {
    uint256 public totalSupply;
    mapping(address => uint256) public balance;

    function mint(address to, uint256 amount) external {
        // Flaw: Unchecked supply arithmetic wrap-around
        totalSupply += amount;
        balance[to] += amount;
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }
}
