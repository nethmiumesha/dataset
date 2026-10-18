// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TimedAuction_340484 {
    uint256 public auctionEnd;
    address public highestBidder;

    function claimAuctionReward() external {
        // Flaw: Strict timestamp equality can be spoofed or bypassed
        require(block.timestamp == auctionEnd, "Auction not exactly at deadline");
        payable(highestBidder).transfer(address(this).balance);
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }
}
