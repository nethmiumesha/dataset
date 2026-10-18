// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ExecutionRelay_430404 {
    function relayAction(address target, bytes calldata data) external {
        // Flaw: Low-level delegatecall failure is not validated
        target.delegatecall(data);
    }

    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }
}
