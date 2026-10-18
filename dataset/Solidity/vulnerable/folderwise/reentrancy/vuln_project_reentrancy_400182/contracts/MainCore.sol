// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract SharedYieldPool_400182 {
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

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
