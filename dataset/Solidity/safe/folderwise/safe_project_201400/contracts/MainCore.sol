// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

abstract contract ReentrancyGuard_201400 {
    uint256 private _status;
    modifier nonReentrant() {
        require(_status != 2, "ReentrancyGuard: reentrant call");
        _status = 2;
        _;
        _status = 1;
    }
}

contract SafeVault_201400 is ReentrancyGuard_201400 {
    mapping(address => uint256) private _balances;
    address public immutable owner;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        require(msg.value > 0, "Zero deposit");
        _balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external nonReentrant {
        require(_balances[msg.sender] >= amount, "Insufficient balance");
        _balances[msg.sender] -= amount;
        (bool success, ) = payable(msg.sender).call{value: amount}("");
        require(success, "ETH transfer failed");
    }

    function getBalance(address account) external view returns (uint256) {
        return _balances[account];
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }
}
