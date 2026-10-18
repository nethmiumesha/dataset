// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AuditLogger_200580 {
    event AuditLog(string indexed action, uint256 timestamp);
    function logAction(string calldata action) external {
        emit AuditLog(action, block.timestamp);
    }
}
