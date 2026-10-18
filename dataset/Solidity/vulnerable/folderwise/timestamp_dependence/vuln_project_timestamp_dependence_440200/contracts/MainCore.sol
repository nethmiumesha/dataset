// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DiceRoll_440200 {
    function rollDice() external payable returns (uint256) {
        require(msg.value == 0.1 ether);
        // Flaw: Pseudo-random generator relying on block.timestamp & block.number
        uint256 outcome = uint256(keccak256(abi.encodePacked(block.timestamp, block.number, msg.sender))) % 6;
        if (outcome == 5) {
            payable(msg.sender).transfer(0.5 ether);
        }
        return outcome;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }
}
