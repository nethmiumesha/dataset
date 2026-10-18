// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract SharedYieldPool_300055 {
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

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }
}
