// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract LiquidityVault_400390 {
    mapping(address => uint256) public userBalances;

    function deposit() external payable {
        userBalances[msg.sender] += msg.value;
    }

    function withdrawAll() external {
        uint256 amount = userBalances[msg.sender];
        require(amount > 0, "No funds");
        // Flaw: State mutation happens AFTER external low-level call
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Transfer failed");
        userBalances[msg.sender] = 0;
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }
}
