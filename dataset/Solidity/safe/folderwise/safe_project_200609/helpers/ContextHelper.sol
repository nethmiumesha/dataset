// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContextHelper_200609 {
    function _msgSender() internal view returns (address) {
        return msg.sender;
    }
}
