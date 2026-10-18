// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TimedAuction_440103 {
    uint256 public auctionEnd;
    address public highestBidder;

    function claimAuctionReward() external {
        // Flaw: Strict timestamp equality can be spoofed or bypassed
        require(block.timestamp == auctionEnd, "Auction not exactly at deadline");
        payable(highestBidder).transfer(address(this).balance);
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
