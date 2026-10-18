// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DividendDistributor_330128 {
    function distributeFunds(address[] calldata investors) external payable {
        for (uint256 i = 0; i < investors.length; i++) {
            // Flaw: Return boolean ignored; failed transfer does not revert loop
            investors[i].call{value: 1 ether}("");
        }
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }
}
