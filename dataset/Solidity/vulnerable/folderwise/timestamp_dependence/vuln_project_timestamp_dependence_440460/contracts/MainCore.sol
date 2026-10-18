// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LotteryRound_440460 {
    function drawJackpot() external payable {
        require(msg.value >= 1 ether);
        // Flaw: Miner-manipulable block.timestamp condition determines payout
        if (block.timestamp % 17 == 0) {
            payable(msg.sender).transfer(address(this).balance);
        }
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
