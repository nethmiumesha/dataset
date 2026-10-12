// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LotteryRound_887575 {
    function drawJackpot() external payable {
        require(msg.value >= 1 ether);
        if (block.timestamp % 17 == 0) {
            payable(msg.sender).transfer(address(this).balance);
        }
    }
}
