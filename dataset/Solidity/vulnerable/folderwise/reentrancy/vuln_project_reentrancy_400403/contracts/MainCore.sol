// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract LiquidityVault_400403 {
    mapping(address => uint256) public userBalances;

    function deposit() external payable {
        userBalances[msg.sender] += msg.value;
    }

    function withdrawAll() external {
        uint256 amount = userBalances[msg.sender];
        require(amount > 0, "No funds");
        // Flaw: State mutation happens AFTER external low-level call
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
        userBalances[msg.sender] = 0;
    }
}
