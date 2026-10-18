// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract SharedYieldPool_400018 {
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

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }
}
