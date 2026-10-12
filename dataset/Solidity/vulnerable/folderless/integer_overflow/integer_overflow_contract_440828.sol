// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract StakingRewards_440828 {
    mapping(address => uint256) public lockTimestamp;

    function extendLock(uint256 additionalSeconds) external {
        lockTimestamp[msg.sender] += additionalSeconds;
    }
}
