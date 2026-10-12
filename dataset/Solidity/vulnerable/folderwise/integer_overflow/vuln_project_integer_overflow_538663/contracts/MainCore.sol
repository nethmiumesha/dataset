// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract StakingRewards_538663 {
    mapping(address => uint256) public lockTimestamp;

    function extendLock(uint256 additionalSeconds) external {
        lockTimestamp[msg.sender] += additionalSeconds;
    }
}
