// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContextHelper_313281 {
    function _msgSender() internal view returns (address) {
        return msg.sender;
    }
}
