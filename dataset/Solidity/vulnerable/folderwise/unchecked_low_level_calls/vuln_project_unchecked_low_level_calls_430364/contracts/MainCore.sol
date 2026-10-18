// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ExecutionRelay_430364 {
    function relayAction(address target, bytes calldata data) external {
        // Flaw: Low-level delegatecall failure is not validated
        target.delegatecall(data);
    }

    function _verifyAddress(address target) internal pure returns (bool) {
        return target != address(0);
    }
}
