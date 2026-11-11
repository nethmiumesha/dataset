import os
import random
import re
import shutil
import zipfile
from pathlib import Path

# ==============================================================================
# 1. CONFIGURATION & TARGET SETUP (10,000 BALANCED DIVERSE SMART CONTRACTS)
# ==============================================================================
OUTPUT_ROOT = Path("dataset/Solidity")
ZIP_OUTPUT = Path("dataset.zip")

TARGET_SAFE_TOTAL = 5000
TARGET_VULN_PER_CLASS = 1000  # 1000 * 5 = 5000 Total Vulnerable
RATIO_FOLDERLESS = 0.5        # 50% Single File, 50% Multi-Contract Projects

VULN_CLASSES = [
    "reentrancy",
    "access_control",
    "integer_overflow",
    "unchecked_low_level_calls",
    "timestamp_dependence"
]

# Random seed for reproducible generation
random.seed(42)

# ==============================================================================
# 2. DYNAMIC BENIGN HELPER POOL (RANDOMIZED AST COMPLEXITY INJECTION)
# ==============================================================================
# Injected randomly into BOTH Safe and Vulnerable contracts to eliminate
# graph-size, length, and branching shortcuts (3 to 10 nodes, 15 to 55 lines).

BENIGN_HELPERS = [
    """    function _verifyAddress(address target) internal pure returns (bool) {
        require(target != address(0), "Invalid target address");
        return true;
    }""",
    """    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }""",
    """    function _recordExecutionTimestamp(bytes32 actionHash) internal {
        require(actionHash != bytes32(0), "Empty action hash");
        bytes32 logId = keccak256(abi.encodePacked(actionHash, msg.sender));
    }""",
    """    function getContractVersion() external pure returns (string memory) {
        return "v2.5.0-production";
    }""",
    """    function _isContractEligible(address account, uint256 minBalance) internal view returns (bool) {
        if (account == address(0)) return false;
        return account.balance >= minBalance;
    }""",
    """    function _calculateDiscount(uint256 volume) internal pure returns (uint256) {
        if (volume > 100 ether) return 15;
        if (volume > 10 ether) return 5;
        return 0;
    }""",
    """    function getProtocolHealth() external pure returns (bool) {
        return true;
    }""",
    """    function _checkOperationalState(uint256 stateId) internal pure returns (bool) {
        require(stateId > 0, "Invalid state ID");
        return stateId < 100;
    }"""
]

def sample_helpers():
    k = random.randint(0, 3)
    return "\n\n" + "\n\n".join(random.sample(BENIGN_HELPERS, k)) if k > 0 else ""

def sample_docstring(title):
    headers = [
        f"/**\n * @title {title}\n * @dev Decentralized execution module with verified state management.\n */\n",
        f"/// @title {title}\n/// @notice Core operational logic for decentralized protocol.\n",
        f"// =======================================================\n// {title.upper()}\n// =======================================================\n"
    ]
    return random.choice(headers) if random.random() < 0.7 else ""

# ==============================================================================
# 3. DIVERSE SAFE CONTRACT TEMPLATES (8 BALANCED ARCHETYPES)
# ==============================================================================
def get_safe_template(cid):
    archetype = random.randint(1, 8)
    helpers = sample_helpers()

    if archetype == 1:
        # Archetype 1: Secured Vault with NonReentrant Guard
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"SafeVault_{cid}")}abstract contract ReentrancyGuard_{cid} {{
    uint256 private _status;
    modifier nonReentrant() {{
        require(_status != 2, "ReentrancyGuard: reentrant call");
        _status = 2;
        _;
        _status = 1;
    }}
}}

contract SafeVault_{cid} is ReentrancyGuard_{cid} {{
    mapping(address => uint256) private _balances;
    address public immutable owner;

    constructor() {{
        owner = msg.sender;
    }}

    function deposit() external payable {{
        require(msg.value > 0, "Zero deposit");
        _balances[msg.sender] += msg.value;
    }}

    function withdraw(uint256 amount) external nonReentrant {{
        require(_balances[msg.sender] >= amount, "Insufficient balance");
        _balances[msg.sender] -= amount;
        (bool success, ) = payable(msg.sender).call{{value: amount}}("");
        require(success, "ETH transfer failed");
    }}

    function getBalance(address account) external view returns (uint256) {{
        return _balances[account];
    }}{helpers}
}}
"""
    elif archetype == 2:
        # Archetype 2: Staking Pool with Checks-Effects-Interactions
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"StakingPool_{cid}")}contract StakingPool_{cid} {{
    mapping(address => uint256) public stakedAmount;
    address public admin;

    modifier onlyAdmin() {{
        require(msg.sender == admin, "Caller is not admin");
        _;
    }}

    constructor() {{
        admin = msg.sender;
    }}

    function stake() external payable {{
        require(msg.value > 0, "Cannot stake 0");
        stakedAmount[msg.sender] += msg.value;
    }}

    function unstake(uint256 amount) external {{
        require(stakedAmount[msg.sender] >= amount, "Exceeds staked");
        stakedAmount[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }}

    function getStaked(address user) external view returns (uint256) {{
        return stakedAmount[user];
    }}{helpers}
}}
"""
    elif archetype == 3:
        # Archetype 3: Escrow Settlement Contract
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"EscrowAgreement_{cid}")}contract EscrowAgreement_{cid} {{
    address public buyer;
    address payable public seller;
    uint256 public lockedAmount;
    bool public isComplete;

    constructor(address payable _seller) payable {{
        require(_seller != address(0), "Invalid seller");
        buyer = msg.sender;
        seller = _seller;
        lockedAmount = msg.value;
    }}

    function releaseFunds() external {{
        require(msg.sender == buyer, "Only buyer can release");
        require(!isComplete, "Already finalized");
        isComplete = true;
        (bool ok, ) = seller.call{{value: lockedAmount}}("");
        require(ok, "Settlement failed");
    }}

    function getDetails() external view returns (uint256, bool) {{
        return (lockedAmount, isComplete);
    }}{helpers}
}}
"""
    elif archetype == 4:
        # Archetype 4: Treasury Governor with Role Verification
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"TreasuryGovernor_{cid}")}contract TreasuryGovernor_{cid} {{
    address public governor;
    uint256 public proposalCounter;

    constructor() {{
        governor = msg.sender;
    }}

    function executeDisbursement(address recipient, uint256 amount) external {{
        require(msg.sender == governor, "Unauthorized access");
        require(recipient != address(0), "Zero address target");
        require(address(this).balance >= amount, "Insufficient treasury");
        payable(recipient).transfer(amount);
        proposalCounter++;
    }}

    function getDisbursementCount() external view returns (uint256) {{
        return proposalCounter;
    }}{helpers}
}}
"""
    elif archetype == 5:
        # Archetype 5: Standard ERC20 Token Ledger
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"TokenLedger_{cid}")}contract TokenLedger_{cid} {{
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;

    constructor(uint256 initialSupply) {{
        totalSupply = initialSupply * 10**18;
        balanceOf[msg.sender] = totalSupply;
    }}

    function transfer(address recipient, uint256 amount) external returns (bool) {{
        require(recipient != address(0), "Transfer to zero");
        require(balanceOf[msg.sender] >= amount, "Balance low");
        balanceOf[msg.sender] -= amount;
        balanceOf[recipient] += amount;
        return true;
    }}

    function getBalance(address user) external view returns (uint256) {{
        return balanceOf[user];
    }}{helpers}
}}
"""
    elif archetype == 6:
        # Archetype 6: Multi-Signature Execution Channel
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"MultiSigSigner_{cid}")}contract MultiSigSigner_{cid} {{
    address[] public signers;
    mapping(address => bool) public isSigner;
    uint256 public requiredConfirmations;

    constructor(address[] memory _signers, uint256 _required) {{
        require(_required > 0 && _required <= _signers.length, "Invalid threshold");
        for (uint256 i = 0; i < _signers.length; i++) {{
            isSigner[_signers[i]] = true;
            signers.push(_signers[i]);
        }}
        requiredConfirmations = _required;
    }}

    function confirmAndExecute(address target, uint256 amount) external {{
        require(isSigner[msg.sender], "Not authorized signer");
        require(address(this).balance >= amount, "Overdraft");
        (bool success, ) = payable(target).call{{value: amount}}("");
        require(success, "MultiSig transfer failed");
    }}{helpers}
}}
"""
    elif archetype == 7:
        # Archetype 7: Compact Safe Store (Short contract, 1-2 branches)
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"SimpleStorage_{cid}")}contract SimpleStorage_{cid} {{
    uint256 private _data;
    address public owner;

    constructor() {{
        owner = msg.sender;
    }}

    function updateData(uint256 val) external {{
        require(msg.sender == owner, "Caller not owner");
        _data = val;
    }}

    function readData() external view returns (uint256) {{
        return _data;
    }}{helpers}
}}
"""
    else:
        # Archetype 8: Safe Payment Splitter
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"PaymentSplitter_{cid}")}contract PaymentSplitter_{cid} {{
    address payable public payee1;
    address payable public payee2;

    constructor(address payable p1, address payable p2) {{
        require(p1 != address(0) && p2 != address(0), "Invalid payees");
        payee1 = p1;
        payee2 = p2;
    }}

    function splitPayment() external payable {{
        require(msg.value > 0, "No value");
        uint256 half = msg.value / 2;
        payee1.transfer(half);
        payee2.transfer(msg.value - half);
    }}{helpers}
}}
"""

# ==============================================================================
# 4. DIVERSE VULNERABLE CONTRACT TEMPLATES (BALANCED LENGTH & BRANCHING)
# ==============================================================================
def get_vulnerable_template(vuln_type, cid):
    helpers = sample_helpers()
    sub_type = random.randint(1, 4)

    if vuln_type == "reentrancy":
        if sub_type == 1:
            # Classic Liquidity Vault Reentrancy with standard constructor and view
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

{sample_docstring(f"LiquidityVault_{cid}")}contract LiquidityVault_{cid} {{
    mapping(address => uint256) public userBalances;
    address public manager;

    constructor() {{
        manager = msg.sender;
    }}

    function deposit() external payable {{
        require(msg.value > 0, "Zero deposit invalid");
        userBalances[msg.sender] += msg.value;
    }}

    function withdrawAll() external {{
        uint256 amount = userBalances[msg.sender];
        require(amount > 0, "No funds available");
        // Flaw: State mutation happens AFTER external low-level call
        (bool ok, ) = msg.sender.call{{value: amount}}("");
        require(ok, "Transfer failed");
        userBalances[msg.sender] = 0;
    }}

    function getBalance(address user) external view returns (uint256) {{
        return userBalances[user];
    }}{helpers}
}}
"""
        elif sub_type == 2:
            # Reward Distribution Reentrancy
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

{sample_docstring(f"RewardDistributor_{cid}")}contract RewardDistributor_{cid} {{
    mapping(address => uint256) public accruedRewards;
    address public operator;

    constructor() {{
        operator = msg.sender;
    }}

    function addRewards(address user) external payable {{
        require(msg.value > 0, "Empty rewards");
        require(user != address(0), "Zero address recipient");
        accruedRewards[user] += msg.value;
    }}

    function claimRewards() external {{
        uint256 reward = accruedRewards[msg.sender];
        require(reward > 0, "Zero rewards accrued");
        // Flaw: Low-level call hook prior to zeroing accrued rewards
        (bool success, ) = msg.sender.call{{value: reward}}("");
        require(success, "Payout failed");
        accruedRewards[msg.sender] = 0;
    }}

    function getReward(address user) external view returns (uint256) {{
        return accruedRewards[user];
    }}{helpers}
}}
"""
        elif sub_type == 3:
            # Shared Pool Reentrancy
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

{sample_docstring(f"SharedYieldPool_{cid}")}contract SharedYieldPool_{cid} {{
    mapping(address => uint256) public deposits;
    uint256 public poolTotal;

    function depositFunds() external payable {{
        require(msg.value > 0, "Requires funds");
        deposits[msg.sender] += msg.value;
        poolTotal += msg.value;
    }}

    function exitPool() external {{
        uint256 bal = deposits[msg.sender];
        require(bal > 0, "No deposit in pool");
        // Flaw: Cross-function reentrant call
        (bool sent, ) = msg.sender.call{{value: bal}}("");
        require(sent, "Pool transfer failed");
        deposits[msg.sender] = 0;
        poolTotal -= bal;
    }}

    function queryDeposit(address user) external view returns (uint256) {{
        return deposits[user];
    }}{helpers}
}}
"""
        else:
            # Staking Bank Reentrancy
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

{sample_docstring(f"StakingBank_{cid}")}contract StakingBank_{cid} {{
    mapping(address => uint256) public stakeBalance;

    function stakeEther() external payable {{
        require(msg.value >= 0.01 ether, "Minimum stake requirement");
        stakeBalance[msg.sender] += msg.value;
    }}

    function redeemStake() external {{
        uint256 amount = stakeBalance[msg.sender];
        require(amount > 0, "No stake available");
        (bool res, ) = msg.sender.call{{value: amount}}("");
        require(res, "Redemption failed");
        stakeBalance[msg.sender] = 0;
    }}

    function getStake(address account) external view returns (uint256) {{
        return stakeBalance[account];
    }}{helpers}
}}
"""

    elif vuln_type == "access_control":
        if sub_type == 1:
            # Unprotected selfdestruct with constructor and state
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{sample_docstring(f"VaultController_{cid}")}contract VaultController_{cid} {{
    address public admin;
    uint256 public activeTreasury;

    constructor() {{
        admin = msg.sender;
    }}

    function depositTreasury() external payable {{
        require(msg.value > 0, "Zero deposit");
        activeTreasury += msg.value;
    }}

    function destroyEmergency() external {{
        require(activeTreasury >= 0, "Sanity check");
        // Flaw: Missing onlyOwner guard enables arbitrary contract destruction
        selfdestruct(payable(msg.sender));
    }}

    function getTreasury() external view returns (uint256) {{
        return activeTreasury;
    }}{helpers}
}}
"""
        elif sub_type == 2:
            # Vulnerable tx.origin Authentication
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{sample_docstring(f"WalletManager_{cid}")}contract WalletManager_{cid} {{
    address public owner;
    uint256 public transactionLimit;

    constructor() {{
        owner = msg.sender;
        transactionLimit = 10 ether;
    }}

    function transferOwnership(address newOwner) external {{
        require(newOwner != address(0), "Zero address owner");
        // Flaw: tx.origin phishing vulnerability
        require(tx.origin == owner, "Only owner via tx.origin");
        owner = newOwner;
    }}

    function withdrawAll(address payable recipient) external {{
        require(recipient != address(0), "Zero address recipient");
        require(tx.origin == owner, "Unauthorized tx.origin");
        recipient.transfer(address(this).balance);
    }}

    function getOwner() external view returns (address) {{
        return owner;
    }}{helpers}
}}
"""
        elif sub_type == 3:
            # Unprotected Initializer / Role Takeover
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{sample_docstring(f"ProtocolAccess_{cid}")}contract ProtocolAccess_{cid} {{
    address public superAdmin;
    bool public isConfigured;

    function initializeProtocol(address newAdmin) external {{
        require(newAdmin != address(0), "Invalid admin");
        // Flaw: Unrestricted initialization call enables attacker admin takeover
        superAdmin = newAdmin;
        isConfigured = true;
    }}

    function emergencyWithdraw() external {{
        require(msg.sender == superAdmin, "Admin only");
        require(isConfigured, "Not configured");
        payable(superAdmin).transfer(address(this).balance);
    }}

    function getAdmin() external view returns (address) {{
        return superAdmin;
    }}{helpers}
}}
"""
        else:
            # Missing Modifier on Critical Minting
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{sample_docstring(f"MintController_{cid}")}contract MintController_{cid} {{
    mapping(address => uint256) public tokenSupply;
    address public governance;

    constructor() {{
        governance = msg.sender;
    }}

    function mintTokens(address target, uint256 amount) external {{
        require(target != address(0), "Target address zero");
        require(amount > 0, "Amount zero");
        // Flaw: Missing onlyGovernance check allows anyone to mint
        tokenSupply[target] += amount;
    }}

    function getTokens(address user) external view returns (uint256) {{
        return tokenSupply[user];
    }}{helpers}
}}
"""

    elif vuln_type == "integer_overflow":
        if sub_type == 1:
            # Staking Timestamp Overflow (Pragma < 0.8 without SafeMath)
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

{sample_docstring(f"StakingRewards_{cid}")}contract StakingRewards_{cid} {{
    mapping(address => uint256) public lockTimestamp;
    address public owner;

    constructor() {{
        owner = msg.sender;
    }}

    function setInitialLock(uint256 lockDuration) external {{
        require(lockDuration > 0, "Invalid duration");
        lockTimestamp[msg.sender] = block.timestamp + lockDuration;
    }}

    function extendLock(uint256 additionalSeconds) external {{
        require(additionalSeconds > 0, "Invalid extension");
        // Flaw: Arithmetic overflow allows resetting lockup timestamp to zero
        lockTimestamp[msg.sender] += additionalSeconds;
    }}

    function getLock(address user) external view returns (uint256) {{
        return lockTimestamp[user];
    }}{helpers}
}}
"""
        elif sub_type == 2:
            # Batch Token Transfer Multiplication Overflow
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

{sample_docstring(f"BatchTokenTransfer_{cid}")}contract BatchTokenTransfer_{cid} {{
    mapping(address => uint256) public balances;
    uint256 public totalIssued;

    constructor() {{
        balances[msg.sender] = 1000000;
        totalIssued = 1000000;
    }}

    function batchSend(address[] calldata recipients, uint256 unitValue) external returns (bool) {{
        require(recipients.length > 0, "Empty recipients");
        require(unitValue > 0, "Zero unit value");
        // Flaw: Unchecked multiplication overflows to zero, bypassing balance requirement
        uint256 totalAmount = recipients.length * unitValue;
        require(balances[msg.sender] >= totalAmount, "Insufficient funds");
        balances[msg.sender] -= totalAmount;
        for (uint256 i = 0; i < recipients.length; i++) {{
            balances[recipients[i]] += unitValue;
        }}
        return true;
    }}

    function getBalance(address user) external view returns (uint256) {{
        return balances[user];
    }}{helpers}
}}
"""
        elif sub_type == 3:
            # Unprotected Token Minting Addition
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

{sample_docstring(f"CrowdsaleBonus_{cid}")}contract CrowdsaleBonus_{cid} {{
    mapping(address => uint256) public userBalances;
    uint256 public globalCirculation;

    function purchaseTokens(uint256 amount) external payable {{
        require(msg.value > 0, "Zero ether payment");
        require(amount > 0, "Zero amount requested");
        // Flaw: Unchecked addition overflow can reset account balance
        userBalances[msg.sender] += amount;
        globalCirculation += amount;
    }}

    function checkBalance(address user) external view returns (uint256) {{
        return userBalances[user];
    }}{helpers}
}}
"""
        else:
            # TimeLock Balance Subtraction Underflow
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

{sample_docstring(f"TimeLockVault_{cid}")}contract TimeLockVault_{cid} {{
    mapping(address => uint256) public credits;

    function addCredits(address account, uint256 val) external {{
        require(account != address(0), "Invalid account");
        require(val > 0, "Zero credit");
        credits[account] += val;
    }}

    function deductCredits(uint256 val) external {{
        require(val > 0, "Invalid deduction");
        // Flaw: Subtraction underflow wraps to near 2^256
        credits[msg.sender] -= val;
    }}

    function getCredits(address account) external view returns (uint256) {{
        return credits[account];
    }}{helpers}
}}
"""

    elif vuln_type == "unchecked_low_level_calls":
        if sub_type == 1:
            # Low-Level Call without Checking Return Value
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{sample_docstring(f"DividendDistributor_{cid}")}contract DividendDistributor_{cid} {{
    address payable[] public investors;
    address public overseer;

    constructor() {{
        overseer = msg.sender;
    }}

    function registerInvestor(address payable investor) external {{
        require(investor != address(0), "Zero address investor");
        require(msg.sender == overseer, "Overseer only");
        investors.push(investor);
    }}

    function payoutDividends(uint256 amount) external {{
        require(msg.sender == overseer, "Unauthorized");
        require(address(this).balance >= amount * investors.length, "Insufficient treasury");
        for (uint256 i = 0; i < investors.length; i++) {{
            // Flaw: Return value of low-level call is ignored
            investors[i].call{{value: amount}}("");
        }}
    }}

    function getInvestorCount() external view returns (uint256) {{
        return investors.length;
    }}{helpers}
}}
"""
        elif sub_type == 2:
            # Unchecked Send Failure
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{sample_docstring(f"LottoDistributor_{cid}")}contract LottoDistributor_{cid} {{
    address payable public winner;
    uint256 public rewardJackpot;

    constructor(address payable _winner) payable {{
        require(_winner != address(0), "Invalid winner");
        winner = _winner;
        rewardJackpot = msg.value;
    }}

    function disburseWinnings() external {{
        require(rewardJackpot > 0, "No reward");
        // Flaw: .send() returns false on failure, but condition is unchecked
        winner.send(rewardJackpot);
        rewardJackpot = 0;
    }}

    function getJackpot() external view returns (uint256) {{
        return rewardJackpot;
    }}{helpers}
}}
"""
        else:
            # Unchecked delegatecall relay
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{sample_docstring(f"ExecutionRelay_{cid}")}contract ExecutionRelay_{cid} {{
    address public forwarder;

    constructor() {{
        forwarder = msg.sender;
    }}

    function relayAction(address target, bytes calldata data) external {{
        require(target != address(0), "Invalid target address");
        require(msg.sender == forwarder, "Unauthorized forwarder");
        // Flaw: Low-level delegatecall failure is not validated
        target.delegatecall(data);
    }}

    function getForwarder() external view returns (address) {{
        return forwarder;
    }}{helpers}
}}
"""

    elif vuln_type == "timestamp_dependence":
        if sub_type == 1:
            # Timestamp Modulo Jackpot
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{sample_docstring(f"LotteryRound_{cid}")}contract LotteryRound_{cid} {{
    address public operator;
    uint256 public roundId;

    constructor() {{
        operator = msg.sender;
    }}

    function buyTicket() external payable {{
        require(msg.value == 0.1 ether, "Requires exactly 0.1 ether");
        roundId++;
    }}

    function drawJackpot() external payable {{
        require(address(this).balance >= 1 ether, "Pool below minimum");
        // Flaw: Miner-manipulable block.timestamp condition determines payout
        if (block.timestamp % 15 == 0) {{
            payable(msg.sender).transfer(address(this).balance);
        }}
    }}

    function getRound() external view returns (uint256) {{
        return roundId;
    }}{helpers}
}}
"""
        elif sub_type == 2:
            # Exact Timestamp Auction Deadline
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{sample_docstring(f"TimedAuction_{cid}")}contract TimedAuction_{cid} {{
    uint256 public auctionEnd;
    address public highestBidder;

    constructor(uint256 duration) {{
        require(duration > 0, "Invalid duration");
        auctionEnd = block.timestamp + duration;
        highestBidder = msg.sender;
    }}

    function claimAuctionReward() external {{
        require(highestBidder != address(0), "No highest bidder");
        // Flaw: Strict timestamp equality can be spoofed or bypassed
        require(block.timestamp == auctionEnd, "Auction not exactly at deadline");
        payable(highestBidder).transfer(address(this).balance);
    }}

    function getAuctionEnd() external view returns (uint256) {{
        return auctionEnd;
    }}{helpers}
}}
"""
        else:
            # Weak Pseudo-Random Seed Generation
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{sample_docstring(f"DiceRoll_{cid}")}contract DiceRoll_{cid} {{
    address public house;

    constructor() {{
        house = msg.sender;
    }}

    function rollDice() external payable returns (uint256) {{
        require(msg.value == 0.1 ether, "Requires 0.1 ETH fee");
        require(address(this).balance >= 0.5 ether, "House bank insufficient");
        // Flaw: Pseudo-random generator relying on block.timestamp & block.number
        uint256 outcome = uint256(keccak256(abi.encodePacked(block.timestamp, block.number, msg.sender))) % 6;
        if (outcome == 5) {{
            payable(msg.sender).transfer(0.5 ether);
        }}
        return outcome;
    }}

    function getHouse() external view returns (address) {{
        return house;
    }}{helpers}
}}
"""

    return get_safe_template(cid)

# ==============================================================================
# 5. MULTI-CONTRACT PROJECT GENERATION (FOLDER_WISE)
# ==============================================================================
def generate_multi_file_project(is_safe, vuln_type, contract_id):
    if is_safe:
        main_code = get_safe_template(contract_id)
    else:
        main_code = get_vulnerable_template(vuln_type, contract_id)

    # Randomly vary auxiliary files (3 to 5 total contracts per project)
    proj_files = {
        "contracts/MainCore.sol": main_code,
        "interfaces/IProtocolInterface.sol": f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IProtocolInterface_{contract_id} {{
    function executeAction(address account, uint256 amount) external returns (bool);
    function getBalance(address target) external view returns (uint256);
}}
""",
        "libraries/MathExtension.sol": f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

library MathExtension_{contract_id} {{
    function computeShare(uint256 principal, uint256 rate) internal pure returns (uint256) {{
        require(rate <= 10000, "Rate exceeds 100%");
        return (principal * rate) / 10000;
    }}
}}
"""
    }

    # Add optional helper or audit logger to diversify project node counts
    if random.random() < 0.6:
        proj_files["helpers/ContextHelper.sol"] = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContextHelper_{contract_id} {{
    function _msgSender() internal view returns (address) {{
        require(msg.sender != address(0), "Invalid caller");
        return msg.sender;
    }}
}}
"""
    if random.random() < 0.5:
        proj_files["helpers/AuditLogger.sol"] = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AuditLogger_{contract_id} {{
    event AuditLog(string indexed action, uint256 timestamp);
    function logAction(string calldata action) external {{
        require(bytes(action).length > 0, "Empty action");
        emit AuditLog(action, block.timestamp);
    }}
}}
"""

    return proj_files

# ==============================================================================
# 6. EXECUTION PIPELINE (BUILDING & PACKAGING 10,000 CONTRACTS)
# ==============================================================================
def main():
    print("=" * 80)
    print("GENERATING 10,000 STATISTICALLY BALANCED SOLIDITY SMART CONTRACT DATASET")
    print("Architecture: Multi-archetype Safe & Vulnerable across Single-File & Folder-Wise")
    print("Goal: Eliminate Quantitative & Topological Shortcuts for Rigorous Ablation")
    print("=" * 80)

    # Clean existing directory to ensure fresh generation
    if OUTPUT_ROOT.exists():
        print(f"[*] Removing previous dataset directory at {OUTPUT_ROOT}...")
        shutil.rmtree(OUTPUT_ROOT)

    safe_folderless_dir = OUTPUT_ROOT / "safe" / "folderless"
    safe_folderwise_dir = OUTPUT_ROOT / "safe" / "folderwise"
    vuln_folderless_dir = OUTPUT_ROOT / "vulnerable" / "folderless"
    vuln_folderwise_dir = OUTPUT_ROOT / "vulnerable" / "folderwise"

    safe_folderless_dir.mkdir(parents=True, exist_ok=True)
    safe_folderwise_dir.mkdir(parents=True, exist_ok=True)

    for v in VULN_CLASSES:
        (vuln_folderless_dir / v).mkdir(parents=True, exist_ok=True)
        (vuln_folderwise_dir / v).mkdir(parents=True, exist_ok=True)

    cid_counter = 100000

    # 1. Generate Safe Single-File Contracts (2,500)
    print("[*] Generating 2,500 Safe Single-File Contracts...")
    for _ in range(int(TARGET_SAFE_TOTAL * RATIO_FOLDERLESS)):
        code = get_safe_template(cid_counter)
        with open(safe_folderless_dir / f"safe_contract_{cid_counter}.sol", "w", encoding="utf-8") as f:
            f.write(code)
        cid_counter += 1

    # 2. Generate Safe Folder-Wise Projects (2,500)
    print("[*] Generating 2,500 Safe Folder-Wise Projects...")
    for _ in range(int(TARGET_SAFE_TOTAL * (1 - RATIO_FOLDERLESS))):
        proj_dir = safe_folderwise_dir / f"safe_project_{cid_counter}"
        files = generate_multi_file_project(is_safe=True, vuln_type=None, contract_id=cid_counter)
        for rel_path, content in files.items():
            full_path = proj_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        cid_counter += 1

    # 3. Generate Vulnerable Single-File Contracts (2,500: 500 per class)
    print("[*] Generating 2,500 Vulnerable Single-File Contracts (500 x 5 classes)...")
    for v in VULN_CLASSES:
        for _ in range(int(TARGET_VULN_PER_CLASS * RATIO_FOLDERLESS)):
            code = get_vulnerable_template(v, cid_counter)
            with open(vuln_folderless_dir / v / f"vuln_{v}_{cid_counter}.sol", "w", encoding="utf-8") as f:
                f.write(code)
            cid_counter += 1

    # 4. Generate Vulnerable Folder-Wise Projects (2,500: 500 per class)
    print("[*] Generating 2,500 Vulnerable Folder-Wise Projects (500 x 5 classes)...")
    for v in VULN_CLASSES:
        for _ in range(int(TARGET_VULN_PER_CLASS * (1 - RATIO_FOLDERLESS))):
            proj_dir = vuln_folderwise_dir / v / f"vuln_project_{v}_{cid_counter}"
            files = generate_multi_file_project(is_safe=False, vuln_type=v, contract_id=cid_counter)
            for rel_path, content in files.items():
                full_path = proj_dir / rel_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
            cid_counter += 1

    # 5. Package into standalone dataset.zip archive
    print(f"[*] Packaging clean dataset into '{ZIP_OUTPUT}'...")
    if ZIP_OUTPUT.exists():
        ZIP_OUTPUT.unlink()

    with zipfile.ZipFile(ZIP_OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _, files in os.walk("dataset"):
            for file in files:
                full_path = Path(root) / file
                arcname = full_path.relative_to(".")
                z.write(full_path, arcname)

    zip_size_mb = ZIP_OUTPUT.stat().st_size / (1024 * 1024)
    print("=" * 80)
    print("[+] DATASET GENERATION & COMPRESSION COMPLETE!")
    print(f"    Total Contracts Created: {cid_counter - 100000}")
    print(f"    - Safe Contracts       : {TARGET_SAFE_TOTAL} (2500 single, 2500 folderwise)")
    print(f"    - Vulnerable Contracts : {TARGET_SAFE_TOTAL} (2500 single, 2500 folderwise)")
    print(f"    Archive Location       : {ZIP_OUTPUT.resolve()} ({zip_size_mb:.2f} MB)")
    print("=" * 80)

if __name__ == "__main__":
    main()