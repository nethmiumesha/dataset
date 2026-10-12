// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContextHelper_271635 {
    function _msgSender() internal view returns (address) {
        return msg.sender;
    }
}
