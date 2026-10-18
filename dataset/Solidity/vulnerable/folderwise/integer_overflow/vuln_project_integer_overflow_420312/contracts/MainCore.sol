// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

contract TokenSupply_420312 {
    uint256 public totalSupply;
    mapping(address => uint256) public balance;

    function mint(address to, uint256 amount) external {
        // Flaw: Unchecked supply arithmetic wrap-around
        totalSupply += amount;
        balance[to] += amount;
    }
}
