// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ExecutionRelay_330283 {
    function relayAction(address target, bytes calldata data) external {
        // Flaw: Low-level delegatecall failure is not validated
        target.delegatecall(data);
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }

    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }
}
