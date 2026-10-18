// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DividendDistributor_430099 {
    function distributeFunds(address[] calldata investors) external payable {
        for (uint256 i = 0; i < investors.length; i++) {
            // Flaw: Return boolean ignored; failed transfer does not revert loop
            investors[i].call{value: 1 ether}("");
        }
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }
}
