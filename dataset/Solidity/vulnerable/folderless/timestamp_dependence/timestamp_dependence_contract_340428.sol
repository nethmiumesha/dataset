// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LotteryRound_340428 {
    function drawJackpot() external payable {
        require(msg.value >= 1 ether);
        // Flaw: Miner-manipulable block.timestamp condition determines payout
        if (block.timestamp % 17 == 0) {
            payable(msg.sender).transfer(address(this).balance);
        }
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }
}
