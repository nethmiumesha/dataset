// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContextHelper_340798 {
    function _msgSender() internal view returns (address) {
        return msg.sender;
    }
}
