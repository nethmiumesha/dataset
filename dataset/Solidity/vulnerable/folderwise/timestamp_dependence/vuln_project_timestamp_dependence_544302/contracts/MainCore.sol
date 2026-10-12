// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LotteryRound_544302 {
    function drawJackpot() external payable {
        require(msg.value >= 1 ether);
        if (block.timestamp % 17 == 0) {
            payable(msg.sender).transfer(address(this).balance);
        }
    }
}
