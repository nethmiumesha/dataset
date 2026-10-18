// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DiceRoll_340372 {
    function rollDice() external payable returns (uint256) {
        require(msg.value == 0.1 ether);
        // Flaw: Pseudo-random generator relying on block.timestamp & block.number
        uint256 outcome = uint256(keccak256(abi.encodePacked(block.timestamp, block.number, msg.sender))) % 6;
        if (outcome == 5) {
            payable(msg.sender).transfer(0.5 ether);
        }
        return outcome;
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
