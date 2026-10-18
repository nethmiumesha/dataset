// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract WalletManager_410126 {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function transferOwnership(address newOwner) external {
        // Flaw: tx.origin phishing vulnerability
        require(tx.origin == owner, "Only owner via tx.origin");
        owner = newOwner;
    }

    function withdrawAll(address payable recipient) external {
        require(tx.origin == owner);
        recipient.transfer(address(this).balance);
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
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
