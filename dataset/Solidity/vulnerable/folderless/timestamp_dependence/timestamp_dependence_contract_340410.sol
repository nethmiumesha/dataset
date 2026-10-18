// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DiceRoll_340410 {
    function rollDice() external payable returns (uint256) {
        require(msg.value == 0.1 ether);
        // Flaw: Pseudo-random generator relying on block.timestamp & block.number
        uint256 outcome = uint256(keccak256(abi.encodePacked(block.timestamp, block.number, msg.sender))) % 6;
        if (outcome == 5) {
            payable(msg.sender).transfer(0.5 ether);
        }
        return outcome;
    }

    function _recordExecutionTimestamp(bytes32 actionHash) internal {
        // Audit log state placeholder
        bytes32 logId = keccak256(abi.encodePacked(actionHash, msg.sender));
    }
}
