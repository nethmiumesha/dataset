// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract RewardDistributor_400340 {
    mapping(address => uint256) public accruedRewards;

    function claimRewards() external {
        uint256 reward = accruedRewards[msg.sender];
        if (reward > 0) {
            // Flaw: Call hook prior to zeroing accrued rewards
            (bool success, ) = msg.sender.call{value: reward}("");
            require(success);
            accruedRewards[msg.sender] = 0;
        }
    }

    function addRewards(address user) external payable {
        accruedRewards[user] += msg.value;
    }
}
