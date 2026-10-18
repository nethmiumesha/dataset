// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract StakingPool_201805 {
    mapping(address => uint256) public stakedAmount;
    mapping(address => uint256) public stakeTimestamp;
    address public admin;

    modifier onlyAdmin() {
        require(msg.sender == admin, "Caller is not admin");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function stake() external payable {
        require(msg.value > 0, "Cannot stake 0");
        stakedAmount[msg.sender] += msg.value;
        stakeTimestamp[msg.sender] = block.timestamp;
    }

    function unstake(uint256 amount) external {
        require(stakedAmount[msg.sender] >= amount, "Exceeds staked");
        stakedAmount[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    function emergencyPause() external onlyAdmin {
        // Administrative safeguard
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
