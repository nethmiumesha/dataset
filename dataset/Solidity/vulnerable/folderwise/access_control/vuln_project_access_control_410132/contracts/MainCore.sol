// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract WalletManager_410132 {
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

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }
}
