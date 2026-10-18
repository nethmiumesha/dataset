// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ExecutionRelay_330195 {
    function relayAction(address target, bytes calldata data) external {
        // Flaw: Low-level delegatecall failure is not validated
        target.delegatecall(data);
    }

    function getProtocolHealth() external pure returns (bool) {
        return true;
    }

    function getContractVersion() external pure returns (string memory) {
        return "v2.4.0-release";
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }
}
