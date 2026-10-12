// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContextHelper_820321 {
    function _msgSender() internal view returns (address) {
        return msg.sender;
    }
}
