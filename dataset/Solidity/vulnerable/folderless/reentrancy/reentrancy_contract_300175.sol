// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

contract LiquidityVault_300175 {
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

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
