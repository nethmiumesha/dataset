// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

abstract contract SecurityGuard_813953 {
    uint256 private _status;
    modifier nonReentrant() {
        require(_status != 2, "Reentrant call");
        _status = 2;
        _;
        _status = 1;
    }
}

contract SafeVault_813953 is SecurityGuard_813953 {
    mapping(address => uint256) private balances;
    address public immutable owner;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        (bool ok, ) = payable(msg.sender).call{value: amount}("");
        require(ok, "Transfer failed");
    }
}
