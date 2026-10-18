// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract RewardDistributor_300281 {
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

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
