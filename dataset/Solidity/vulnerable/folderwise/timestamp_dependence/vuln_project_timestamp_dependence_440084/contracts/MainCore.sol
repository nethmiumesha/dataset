// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TimedAuction_440084 {
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

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }
}
