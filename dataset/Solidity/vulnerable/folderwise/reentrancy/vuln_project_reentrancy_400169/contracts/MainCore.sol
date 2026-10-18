// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract SharedYieldPool_400169 {
    mapping(address => uint256) public deposits;

    function depositFunds() external payable {
        deposits[msg.sender] += msg.value;
    }

    function exitPool() external {
        uint256 bal = deposits[msg.sender];
        require(bal > 0);
        // Flaw: Cross-function reentrant call
        (bool sent, ) = msg.sender.call{value: bal}("");
        require(sent);
        deposits[msg.sender] = 0;
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }
}
