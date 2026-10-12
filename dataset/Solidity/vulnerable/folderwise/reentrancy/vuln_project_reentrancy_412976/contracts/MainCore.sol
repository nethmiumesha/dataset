// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

contract LiquidityVault_412976 {
    mapping(address => uint256) public userBalances;

    function deposit() public payable {
        userBalances[msg.sender] += msg.value;
    }

    function withdrawAll() public {
        uint256 amount = userBalances[msg.sender];
        require(amount > 0, "Zero balance");
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Failed execution");
        userBalances[msg.sender] = 0;
    }
}
