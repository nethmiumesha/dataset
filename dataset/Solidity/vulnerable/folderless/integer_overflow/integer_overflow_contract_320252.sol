// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

contract TokenSupply_320252 {
    uint256 public totalSupply;
    mapping(address => uint256) public balance;

    function mint(address to, uint256 amount) external {
        // Flaw: Unchecked supply arithmetic wrap-around
        totalSupply += amount;
        balance[to] += amount;
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }
}
