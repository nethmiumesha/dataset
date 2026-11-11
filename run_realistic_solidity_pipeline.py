import os
import sys
import re
import copy
import json
import random
import shutil
import zipfile
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GATv2Conv, GINConv, global_mean_pool, global_max_pool

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score, recall_score,
    f1_score, matthews_corrcoef, roc_auc_score, average_precision_score,
    confusion_matrix, precision_recall_curve, roc_curve
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def seed_everything(seed=42):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)

seed_everything(42)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[+] Execution Device: {DEVICE}")

# ==============================================================================
# 1. REALISTIC SOLIDITY CONTRACT TEMPLATE GENERATORS
# ==============================================================================
BENIGN_HELPERS = [
    """    function _verifyAddress(address target) internal pure returns (bool) {
        if (target == address(0)) return false;
        return true;
    }""",
    """    function _computeProtocolFee(uint256 amount, uint256 feeBps) internal pure returns (uint256) {
        if (amount == 0 || feeBps == 0) return 0;
        return (amount * feeBps) / 10000;
    }""",
    """    function _recordExecutionTimestamp(bytes32 actionHash) internal view {
        bytes32 logId = keccak256(abi.encodePacked(actionHash, msg.sender, block.timestamp));
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
        return stateId > 0 && stateId < 100;
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

def get_safe_template(cid):
    helpers = sample_helpers()
    # 70% Standard Safe Archetypes (explicit guards), 30% Ambiguous Safe Archetypes (hooks without standard guard keywords)
    is_ambiguous = (random.random() < 0.30)

    if not is_ambiguous:
        archetype = random.randint(1, 4)
        if archetype == 1:
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"SafeVault_{cid}")}contract SafeVault_{cid} {{
    mapping(address => uint256) private _balances;
    address public immutable owner;
    uint256 private _status;

    modifier nonReentrant() {{
        require(_status != 2, "ReentrancyGuard: reentrant call");
        _status = 2;
        _;
        _status = 1;
    }}

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
        else:
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
    else:
        # Ambiguous Safe: Safe logic using Checks-Effects, custom state locks or balance checks WITHOUT require/assert/revert/nonreentrant keywords
        sub = random.randint(1, 3)
        if sub == 1:
            # Custom mutex flag with return (no revert keyword) + low-level call hook
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"CustomLockedVault_{cid}")}contract CustomLockedVault_{cid} {{
    mapping(address => uint256) private userBalance;
    uint256 private _mutexState;

    function deposit() external payable {{
        if (msg.value == 0) return;
        userBalance[msg.sender] += msg.value;
    }}

    function withdraw(uint256 amount) external {{
        if (_mutexState != 0) return;
        if (userBalance[msg.sender] < amount) return;
        _mutexState = 1;
        userBalance[msg.sender] -= amount;
        (bool sent, ) = payable(msg.sender).call{{value: amount}}("");
        if (!sent) {{
            userBalance[msg.sender] += amount;
        }}
        _mutexState = 0;
    }}

    function checkUserBalance(address user) external view returns (uint256) {{
        return userBalance[user];
    }}{helpers}
}}
"""
        elif sub == 2:
            # Pull-payment pattern with internal accounting and state decrement before transfer
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"PullPaymentEscrow_{cid}")}contract PullPaymentEscrow_{cid} {{
    mapping(address => uint256) public pendingWithdrawals;
    address public master;

    constructor() {{
        master = msg.sender;
    }}

    function creditAccount(address user, uint256 amount) external payable {{
        if (msg.sender != master) return;
        if (msg.value < amount) return;
        pendingWithdrawals[user] += amount;
    }}

    function pullFunds() external {{
        uint256 bal = pendingWithdrawals[msg.sender];
        if (bal == 0) return;
        pendingWithdrawals[msg.sender] = 0;
        (bool success, ) = msg.sender.call{{value: bal}}("");
        if (!success) {{
            pendingWithdrawals[msg.sender] = bal;
        }}
    }}

    function queryPending(address target) external view returns (uint256) {{
        return pendingWithdrawals[target];
    }}{helpers}
}}
"""
        else:
            # Unchecked gas-optimized math within safe bounds
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"GasOptimizedPool_{cid}")}contract GasOptimizedPool_{cid} {{
    mapping(address => uint256) public accountShares;
    uint256 public totalShareVolume;

    function addShares(uint256 qty) external payable {{
        if (qty == 0 || msg.value == 0) return;
        unchecked {{
            accountShares[msg.sender] += qty;
            totalShareVolume += qty;
        }}
    }}

    function redeemShares(uint256 qty) external {{
        if (accountShares[msg.sender] < qty) return;
        unchecked {{
            accountShares[msg.sender] -= qty;
            totalShareVolume -= qty;
        }}
        payable(msg.sender).transfer(qty);
    }}

    function getShares(address user) external view returns (uint256) {{
        return accountShares[user];
    }}{helpers}
}}
"""

def get_vulnerable_template(vuln_type, cid):
    helpers = sample_helpers()
    # 70% Blatant Vulnerabilities, 30% Guarded Vulnerabilities (has require/assert but logic flawed)
    is_guarded = (random.random() < 0.30)

    if vuln_type == "reentrancy":
        if is_guarded:
            # Guarded Reentrancy: Contains require guards, but performs call BEFORE zeroing balance
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"GuardedReentrancy_{cid}")}contract GuardedReentrancy_{cid} {{
    mapping(address => uint256) public balances;
    address public auditor;

    constructor() {{
        auditor = msg.sender;
    }}

    function deposit() external payable {{
        require(msg.value > 0, "Zero deposit not allowed");
        require(msg.sender != address(0), "Invalid caller address");
        balances[msg.sender] += msg.value;
    }}

    function withdrawAll() external {{
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance to withdraw");
        require(msg.sender != address(0), "Invalid caller");
        // Flaw: Syntactic require guards exist, but call happens BEFORE state mutation
        (bool ok, ) = msg.sender.call{{value: amount}}("");
        require(ok, "Transfer call failed");
        balances[msg.sender] = 0;
    }}

    function getBalance(address user) external view returns (uint256) {{
        return balances[user];
    }}{helpers}
}}
"""
        else:
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

    elif vuln_type == "access_control":
        if is_guarded:
            # Guarded Access Control: Has require guard, but checks tx.origin (phishing vulnerability)
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"PhishingWallet_{cid}")}contract PhishingWallet_{cid} {{
    address public owner;
    uint256 public dailyLimit;

    constructor() {{
        owner = msg.sender;
        dailyLimit = 10 ether;
    }}

    function transferOwnership(address newOwner) external {{
        require(newOwner != address(0), "Zero address owner");
        // Flaw: Syntactic require guard exists, but tx.origin is vulnerable to phishing
        require(tx.origin == owner, "Only owner can transfer");
        owner = newOwner;
    }}

    function emergencyWithdraw(address payable target) external {{
        require(target != address(0), "Invalid target");
        require(tx.origin == owner, "Unauthorized tx.origin caller");
        target.transfer(address(this).balance);
    }}

    function getOwner() external view returns (address) {{
        return owner;
    }}{helpers}
}}
"""
        else:
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
        // Flaw: Missing authorization modifier on critical selfdestruct
        selfdestruct(payable(msg.sender));
    }}

    function getTreasury() external view returns (uint256) {{
        return activeTreasury;
    }}{helpers}
}}
"""

    elif vuln_type == "integer_overflow":
        if is_guarded:
            # Guarded Integer Overflow: Has require checks on inputs, but uses unchecked math block without upper bound
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"UncheckedMathPool_{cid}")}contract UncheckedMathPool_{cid} {{
    mapping(address => uint256) public userBalances;

    function addBalance(address target, uint256 amount) external {{
        require(target != address(0), "Invalid target address");
        require(amount > 0, "Amount must be positive");
        // Flaw: Unchecked arithmetic causes silent integer overflow despite require guards
        unchecked {{
            userBalances[target] += amount;
        }}
    }}

    function subtractBalance(uint256 amount) external {{
        require(amount > 0, "Amount must be positive");
        unchecked {{
            userBalances[msg.sender] -= amount;
        }}
    }}

    function getBalance(address target) external view returns (uint256) {{
        return userBalances[target];
    }}{helpers}
}}
"""
        else:
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
        // Flaw: Subtraction underflow in pragma ^0.7.6 wraps to 2^256 - 1
        credits[msg.sender] -= val;
    }}

    function getCredits(address account) external view returns (uint256) {{
        return credits[account];
    }}{helpers}
}}
"""

    elif vuln_type == "unchecked_low_level_calls":
        if is_guarded:
            # Low level call with require on inputs, but ignored boolean result
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"PartialCheckRelay_{cid}")}contract PartialCheckRelay_{cid} {{
    address payable public operator;

    constructor() {{
        operator = payable(msg.sender);
    }}

    function disburse(address payable target, uint256 amount) external {{
        require(msg.sender == operator, "Caller is not operator");
        require(target != address(0), "Zero address recipient");
        require(address(this).balance >= amount, "Insufficient reserve");
        // Flaw: Input guards are present, but low-level call return status is ignored
        target.call{{value: amount}}("");
    }}

    function getOperator() external view returns (address) {{
        return operator;
    }}{helpers}
}}
"""
        else:
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

    else: # timestamp_dependence
        if is_guarded:
            return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

{sample_docstring(f"GuardedTimedJackpot_{cid}")}contract GuardedTimedJackpot_{cid} {{
    address public owner;
    uint256 public roundCount;

    constructor() {{
        owner = msg.sender;
    }}

    function enterLottery() external payable {{
        require(msg.value == 0.05 ether, "Exact 0.05 ETH required");
        roundCount++;
    }}

    function claimJackpot() external {{
        require(msg.sender != address(0), "Invalid caller");
        require(address(this).balance >= 0.5 ether, "Insufficient jackpot balance");
        // Flaw: Has require guards, but payout condition is miner-manipulable timestamp
        if (block.timestamp % 17 == 0) {{
            payable(msg.sender).transfer(address(this).balance);
        }}
    }}

    function getRounds() external view returns (uint256) {{
        return roundCount;
    }}{helpers}
}}
"""
        else:
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

def generate_multi_file_project(is_safe, vuln_type, contract_id):
    if is_safe:
        main_code = get_safe_template(contract_id)
    else:
        main_code = get_vulnerable_template(vuln_type, contract_id)

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
        if (rate > 10000) return 0;
        return (principal * rate) / 10000;
    }}
}}
"""
    }
    if random.random() < 0.6:
        proj_files["helpers/ContextHelper.sol"] = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ContextHelper_{contract_id} {{
    function _msgSender() internal view returns (address) {{
        return msg.sender;
    }}
}}
"""
    return proj_files

# ==============================================================================
# 2. FEATURE EXTRACTION & GRAPH SYNTHESIS
# ==============================================================================
def extract_solidity_12d_features(chunk_code, full_contract_low, is_hub=False):
    lines = chunk_code.splitlines()
    c_low = chunk_code.lower()

    f0_len = min(len(lines) / 60.0, 1.0)
    branch_count = len(re.findall(r"\b(?:if|for|while|assembly|require|assert)\b", c_low))
    f1_branch = min(branch_count / 5.0, 1.0)
    f2_scope = float(bool(re.search(r"\b(?:function|modifier|constructor|contract|library|interface)\b", c_low)))
    f3_vis = float(bool(re.search(r"\b(?:public|external)\b", c_low)))
    f4_hook = float(bool(re.search(
        r"\bdelegatecall\b|\bselfdestruct\b|\bsuicide\b|\.call\s*\{|\.call\s*\(|\.call\.value\s*\(|\.(?:transfer|send)\s*\(",
        c_low
    )))
    f5_guard = float(bool(re.search(
        r"\brequire\s*\(|\bassert\s*\(|\brevert\s*\(|\brevert\b|\bmodifier\b|\bonlyowner\b|\bnonreentrant\b",
        c_low
    )))
    has_arith = bool(re.search(r"(?<![=<>!])(?:\+|\-|\*|\/)(?![=<>])", c_low))
    is_protected_math = ("safemath" in full_contract_low) or ("pragma solidity ^0.8" in full_contract_low and "unchecked" not in c_low)
    f6_arith = 1.0 if (has_arith and not is_protected_math) else 0.0
    f7_mutate = float(bool(re.search(r"(?<![=!<>])=(?![=])", c_low)))
    f8_evm = 1.0
    f9_sealevel = 0.0
    f10_pythonic = 0.0
    f11_hub = 1.0 if is_hub else 0.0

    return [
        f0_len, f1_branch, f2_scope, f3_vis, f4_hook, f5_guard,
        f6_arith, f7_mutate, f8_evm, f9_sealevel, f10_pythonic, f11_hub
    ]

def parse_solidity_code(content):
    blocks = re.split(
        r"(?m)(?=^\s*(?:function|modifier|constructor|fallback|receive|contract|library|interface)\b)",
        content
    )
    chunks = [b.strip() for b in blocks if b.strip() and len(b.strip()) > 8]
    if not chunks:
        chunks = [content.strip() or "// empty"]
    return chunks

def build_single_file_graph(content, file_path):
    chunks = parse_solidity_code(content)
    full_low = content.lower()
    features = []
    for i, c in enumerate(chunks):
        feat = extract_solidity_12d_features(c, full_low, is_hub=(i == 0))
        features.append(feat)

    n = len(features)
    edges = []
    for i in range(n - 1):
        edges.extend([(i, i + 1), (i + 1, i)])
    for i in range(1, n):
        edges.extend([(0, i), (i, 0)])
    if n == 1:
        edges.append((0, 0))

    x = torch.tensor(features, dtype=torch.float32)
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    data = Data(x=x, edge_index=edge_index)
    data.file_path = file_path
    return data

def build_folderwise_graph(file_dict, project_path):
    combined_code = "\n".join(file_dict.values())
    combined_low = combined_code.lower()
    total_lines = sum(len(c.splitlines()) for c in file_dict.values())

    hub_chunk = f"// Project Root Hub\n// Files: {len(file_dict)}\n// Lines: {total_lines}\n"
    hub_feat = extract_solidity_12d_features(hub_chunk, combined_low, is_hub=True)

    features = [hub_feat]
    edges = []
    curr_idx = 1

    for fname, code in file_dict.items():
        file_chunks = parse_solidity_code(code)
        file_low = code.lower()
        file_nodes = []

        for chunk in file_chunks:
            feat = extract_solidity_12d_features(chunk, file_low, is_hub=False)
            features.append(feat)
            file_nodes.append(curr_idx)
            curr_idx += 1

        for j in range(len(file_nodes) - 1):
            edges.extend([(file_nodes[j], file_nodes[j + 1]), (file_nodes[j + 1], file_nodes[j])])
        for u in file_nodes:
            edges.extend([(0, u), (u, 0)])

    if len(features) == 1:
        edges.append((0, 0))

    x = torch.tensor(features, dtype=torch.float32)
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    data = Data(x=x, edge_index=edge_index)
    data.file_path = project_path
    return data

# ==============================================================================
# 3. GNN ARCHITECTURE
# ==============================================================================
class GenericLanguageGNN(nn.Module):
    def __init__(self, in_channels, hidden_channels=64, num_classes=2):
        super(GenericLanguageGNN, self).__init__()
        self.input_proj = nn.Linear(in_channels, hidden_channels)
        self.gat = GATv2Conv(hidden_channels, hidden_channels, heads=4, concat=False, dropout=0.08)
        self.ln1 = nn.LayerNorm(hidden_channels)
        gin_mlp = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels),
            nn.BatchNorm1d(hidden_channels),
            nn.GELU(),
            nn.Linear(hidden_channels, hidden_channels)
        )
        self.gin = GINConv(gin_mlp)
        self.ln2 = nn.LayerNorm(hidden_channels)
        self.fc_pool = nn.Linear(hidden_channels * 2, 64)
        self.fc_latent = nn.Linear(64, 32)
        self.dropout = nn.Dropout(0.20)
        self.classifier = nn.Sequential(
            nn.Linear(32, 32),
            nn.LayerNorm(32),
            nn.GELU(),
            nn.Dropout(0.15),
            nn.Linear(32, num_classes)
        )

    def forward(self, x, edge_index, batch):
        h0 = F.gelu(self.input_proj(x))
        h_gat = F.gelu(self.gat(h0, edge_index))
        h1 = self.ln1(h_gat + h0)
        h_gin = F.gelu(self.gin(h1, edge_index))
        h2 = self.ln2(h_gin + h1)
        pool = torch.cat([global_mean_pool(h2, batch), global_max_pool(h2, batch)], dim=1)
        h_struct_32 = F.gelu(self.fc_latent(self.dropout(F.gelu(self.fc_pool(pool)))))
        logits = self.classifier(h_struct_32)
        return logits, h_struct_32

def slice_features(batch_x, mode):
    m = mode.lower().replace("-only", "").replace(" 12d", "").strip()
    if "quant" in m:
        return batch_x[:, 0:2].clone()
    elif "qual" in m:
        return batch_x[:, 2:8].clone()
    elif "context" in m or "topology" in m:
        return batch_x[:, 8:12].clone()
    elif "combined" in m or "12d" in m or "all" in m:
        return batch_x[:, 0:12].clone()
    else:
        raise ValueError(f"Unknown feature mode: {mode}")

# ==============================================================================
# 4. DATASET GENERATION & BENCHMARK EXECUTION
# ==============================================================================
def main():
    print("=" * 80)
    print("STARTING REALISTIC SOLIDITY DATASET GENERATION & GNN BENCHMARK")
    print("=" * 80)

    dataset_root = Path("d:/my_research/research/dataset/Solidity")
    vuln_classes = ["reentrancy", "access_control", "integer_overflow", "unchecked_low_level_calls", "timestamp_dependence"]

    print("[*] Generating 10,000 statistically calibrated realistic Solidity smart contracts...")
    if dataset_root.exists():
        shutil.rmtree(dataset_root)

    safe_single_dir = dataset_root / "safe" / "folderless"
    safe_folder_dir = dataset_root / "safe" / "folderwise"
    vuln_single_dir = dataset_root / "vulnerable" / "folderless"
    vuln_folder_dir = dataset_root / "vulnerable" / "folderwise"

    safe_single_dir.mkdir(parents=True, exist_ok=True)
    safe_folder_dir.mkdir(parents=True, exist_ok=True)
    for v in vuln_classes:
        (vuln_single_dir / v).mkdir(parents=True, exist_ok=True)
        (vuln_folder_dir / v).mkdir(parents=True, exist_ok=True)

    cid = 100000

    # 1. Safe Single Files (2,500)
    print("  [-] Generating 2,500 Safe Single-File Contracts...")
    for _ in range(2500):
        code = get_safe_template(cid)
        with open(safe_single_dir / f"safe_contract_{cid}.sol", "w", encoding="utf-8") as f:
            f.write(code)
        cid += 1

    # 2. Safe Folderwise Projects (2,500)
    print("  [-] Generating 2,500 Safe Folder-Wise Projects...")
    for _ in range(2500):
        pdir = safe_folder_dir / f"safe_project_{cid}"
        files = generate_multi_file_project(is_safe=True, vuln_type=None, contract_id=cid)
        for rpath, ctext in files.items():
            fpath = pdir / rpath
            fpath.parent.mkdir(parents=True, exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(ctext)
        cid += 1

    # 3. Vulnerable Single Files (2,500: 500 per class)
    print("  [-] Generating 2,500 Vulnerable Single-File Contracts...")
    for v in vuln_classes:
        for _ in range(500):
            code = get_vulnerable_template(v, cid)
            with open(vuln_single_dir / v / f"vuln_{v}_{cid}.sol", "w", encoding="utf-8") as f:
                f.write(code)
            cid += 1

    # 4. Vulnerable Folderwise Projects (2,500: 500 per class)
    print("  [-] Generating 2,500 Vulnerable Folder-Wise Projects...")
    for v in vuln_classes:
        for _ in range(500):
            pdir = vuln_folder_dir / v / f"vuln_project_{v}_{cid}"
            files = generate_multi_file_project(is_safe=False, vuln_type=v, contract_id=cid)
            for rpath, ctext in files.items():
                fpath = pdir / rpath
                fpath.parent.mkdir(parents=True, exist_ok=True)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(ctext)
            cid += 1

    print("[+] Dataset generation complete! Total 10,000 contracts synthesized.")

    # Build PyG Graphs
    print("\n[*] Synthesizing PyTorch Geometric Graph Objects from real files...")
    graphs = []
    
    # Walk Single Files
    for root, _, files in os.walk(safe_single_dir):
        for f in files:
            if f.endswith(".sol"):
                with open(os.path.join(root, f), "r", encoding="utf-8") as fp:
                    g = build_single_file_graph(fp.read(), os.path.join(root, f))
                    g.y = torch.tensor([0], dtype=torch.long)
                    graphs.append(g)

    for root, _, files in os.walk(vuln_single_dir):
        for f in files:
            if f.endswith(".sol"):
                with open(os.path.join(root, f), "r", encoding="utf-8") as fp:
                    g = build_single_file_graph(fp.read(), os.path.join(root, f))
                    g.y = torch.tensor([1], dtype=torch.long)
                    graphs.append(g)

    # Walk Folderwise Projects
    def collect_projects(base_dir, label):
        projs = defaultdict(dict)
        for root, _, files in os.walk(base_dir):
            for f in files:
                if f.endswith(".sol"):
                    rel = os.path.relpath(os.path.join(root, f), base_dir).replace("\\", "/")
                    parts = rel.split("/")
                    pname = parts[0] if label == 0 else parts[1] # if vuln, parts[0] is class name
                    with open(os.path.join(root, f), "r", encoding="utf-8") as fp:
                        projs[pname][f] = fp.read()
        for pdir, fdict in projs.items():
            g = build_folderwise_graph(fdict, pdir)
            g.y = torch.tensor([label], dtype=torch.long)
            graphs.append(g)

    collect_projects(safe_folder_dir, 0)
    collect_projects(vuln_folder_dir, 1)

    print(f"[+] Total graphs created: {len(graphs)} (Safe: {sum(1 for g in graphs if g.y.item()==0)}, Vuln: {sum(1 for g in graphs if g.y.item()==1)})")

    # Stratified 80/10/10 split
    labels = [int(g.y.item()) for g in graphs]
    train_g, holdout_g = train_test_split(graphs, test_size=0.20, random_state=42, stratify=labels)
    holdout_labels = [int(g.y.item()) for g in holdout_g]
    val_g, test_g = train_test_split(holdout_g, test_size=0.50, random_state=42, stratify=holdout_labels)

    train_loader = DataLoader(train_g, batch_size=128, shuffle=True)
    val_loader = DataLoader(val_g, batch_size=128, shuffle=False)
    test_loader = DataLoader(test_g, batch_size=128, shuffle=False)

    def collect_probs(model, loader, mode):
        model.eval()
        probs_list, targets_list = [], []
        with torch.no_grad():
            for batch in loader:
                batch = batch.to(DEVICE)
                x_in = slice_features(batch.x, mode)
                logits, _ = model(x_in, batch.edge_index, batch.batch)
                probs = F.softmax(logits, dim=1)[:, 1]
                probs_list.extend(probs.cpu().numpy())
                targets_list.extend(batch.y.cpu().numpy())
        return np.asarray(probs_list), np.asarray(targets_list)

    def train_ablation(mode_name, in_channels, epochs=25):
        print(f"\n[SOLIDITY] TRAINING ABLATION: [{mode_name.upper()}] (in_channels = {in_channels})")
        model = GenericLanguageGNN(in_channels=in_channels, hidden_channels=64, num_classes=2).to(DEVICE)
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=3)
        criterion = nn.CrossEntropyLoss()

        best_val_loss = float("inf")
        best_weights = None
        patience, no_improve = 6, 0

        for epoch in range(1, epochs + 1):
            model.train()
            train_loss = 0.0
            for batch in train_loader:
                batch = batch.to(DEVICE)
                x_in = slice_features(batch.x, mode_name)
                optimizer.zero_grad()
                logits, _ = model(x_in, batch.edge_index, batch.batch)
                loss = criterion(logits, batch.y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
                optimizer.step()
                train_loss += loss.item() * batch.num_graphs

            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for batch in val_loader:
                    batch = batch.to(DEVICE)
                    x_in = slice_features(batch.x, mode_name)
                    logits, _ = model(x_in, batch.edge_index, batch.batch)
                    val_loss += criterion(logits, batch.y).item() * batch.num_graphs

            avg_train = train_loss / len(train_g)
            avg_val = val_loss / len(val_g)
            scheduler.step(avg_val)

            if avg_val < best_val_loss - 1e-4:
                best_val_loss = avg_val
                best_weights = copy.deepcopy(model.state_dict())
                no_improve = 0
            else:
                no_improve += 1

            if epoch == 1 or epoch % 5 == 0 or no_improve >= patience:
                print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_train:.4f} | Val Loss: {avg_val:.4f}")

            if no_improve >= patience:
                print(f"  [!] Early stopping at epoch {epoch}.")
                break

        model.load_state_dict(best_weights)

        val_probs, val_targets = collect_probs(model, val_loader, mode_name)
        precisions, recalls, pr_thresholds = precision_recall_curve(val_targets, val_probs)
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-8)
        best_f1_idx = int(np.argmax(f1_scores))
        optimal_th = float(pr_thresholds[best_f1_idx]) if best_f1_idx < len(pr_thresholds) else 0.50
        optimal_th = float(np.clip(optimal_th, 0.40, 0.60))

        test_probs, test_targets = collect_probs(model, test_loader, mode_name)
        test_preds = (test_probs >= optimal_th).astype(int)

        cm = confusion_matrix(test_targets, test_preds, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()

        test_acc = accuracy_score(test_targets, test_preds) * 100.0
        bal_acc = balanced_accuracy_score(test_targets, test_preds) * 100.0
        prec = precision_score(test_targets, test_preds, zero_division=0) * 100.0
        rec = recall_score(test_targets, test_preds, zero_division=0) * 100.0
        f1 = f1_score(test_targets, test_preds, zero_division=0) * 100.0
        roc_auc = roc_auc_score(test_targets, test_probs)
        pr_auc = average_precision_score(test_targets, test_probs)
        mcc = matthews_corrcoef(test_targets, test_preds)

        print(f"  [+] Calibrated Th: {optimal_th:.4f} | Acc: {test_acc:.2f}% | Rec: {rec:.2f}% | F1: {f1:.2f}% | ROC-AUC: {roc_auc:.4f}")
        print(f"  [+] Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")

        return {
            "Feature_Configuration": mode_name,
            "Feature_Count": in_channels,
            "Accuracy (%)": test_acc,
            "Balanced Accuracy (%)": bal_acc,
            "Precision (%)": prec,
            "Recall / Sensitivity (%)": rec,
            "Macro F1-Score (%)": f1,
            "ROC-AUC Score": roc_auc,
            "PR-AUC (Average Precision)": pr_auc,
            "Matthews Correlation Coefficient (MCC)": mcc,
            "Optimal Calibrated Threshold": optimal_th,
            "Confusion_Matrix": cm,
            "Targets": test_targets,
            "Predictions": test_preds,
            "Probabilities": test_probs,
            "Model": model
        }

    ablation_configs = [
        ("Quantitative-Only", 2),
        ("Qualitative-Only", 6),
        ("Context/Topology-Only", 4),
        ("Combined 12D", 12)
    ]

    benchmark_records = []
    eval_dict = {}

    for mode, dim in ablation_configs:
        res = train_ablation(mode, dim, epochs=25)
        benchmark_records.append({k: v for k, v in res.items() if k not in ["Targets", "Predictions", "Probabilities", "Model", "Confusion_Matrix"]})
        eval_dict[mode] = res

    df_benchmark = pd.DataFrame(benchmark_records)
    csv_file = "d:/my_research/research/solidity_feature_ablation_benchmark.csv"
    df_benchmark.to_csv(csv_file, index=False)
    print(f"\n[+] Saved genuine ablation benchmark to: {csv_file}")
    print(df_benchmark[["Feature_Configuration", "Accuracy (%)", "Recall / Sensitivity (%)", "Macro F1-Score (%)", "ROC-AUC Score"]])

    # Save real model
    combined_model = eval_dict["Combined 12D"]["Model"]
    torch.save(combined_model.state_dict(), "d:/my_research/research/solidity_gnn.pt")
    print("[+] Saved genuine trained PyTorch weights to: d:/my_research/research/solidity_gnn.pt")

    # Generate 4-panel confusion matrix
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.flatten()
    for idx, (mode, _) in enumerate(ablation_configs):
        cm = eval_dict[mode]["Confusion_Matrix"]
        ax = axes[idx]
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax, annot_kws={"size": 14, "weight": "bold"})
        ax.set_title(f"{mode}\nAcc: {eval_dict[mode]['Accuracy (%)']:.2f}% | F1: {eval_dict[mode]['Macro F1-Score (%)']:.2f}%", fontsize=12, fontweight="bold")
        ax.set_xlabel("Predicted Label (0=Safe, 1=Vuln)", fontsize=10)
        ax.set_ylabel("True Label (0=Safe, 1=Vuln)", fontsize=10)
        ax.set_xticklabels(["Safe", "Vulnerable"])
        ax.set_yticklabels(["Safe", "Vulnerable"])
    plt.tight_layout()
    plt.savefig("d:/my_research/research/solidity_4panel_confusion_matrices.png", dpi=300)
    plt.close()
    print("[+] Generated real confusion matrices: d:/my_research/research/solidity_4panel_confusion_matrices.png")

    # Generate Combined ROC and PR curves
    fig, (ax_roc, ax_pr) = plt.subplots(1, 2, figsize=(16, 6))
    colors = ["#7f7f7f", "#2ca02c", "#ff7f0e", "#1f77b4"]
    for idx, (mode, _) in enumerate(ablation_configs):
        t = eval_dict[mode]["Targets"]
        p = eval_dict[mode]["Probabilities"]
        fpr, tpr, _ = roc_curve(t, p)
        ra = eval_dict[mode]["ROC-AUC Score"]
        ax_roc.plot(fpr, tpr, label=f"{mode} (AUC = {ra:.3f})", color=colors[idx], lw=2)

        prec, rec, _ = precision_recall_curve(t, p)
        pa = eval_dict[mode]["PR-AUC (Average Precision)"]
        ax_pr.plot(rec, prec, label=f"{mode} (AP = {pa:.3f})", color=colors[idx], lw=2)

    ax_roc.plot([0, 1], [0, 1], "k--", alpha=0.6)
    ax_roc.set_title("Solidity ROC Curves across Feature Ablations", fontweight="bold")
    ax_roc.set_xlabel("False Positive Rate")
    ax_roc.set_ylabel("True Positive Rate")
    ax_roc.legend()
    ax_roc.grid(True, alpha=0.3)

    ax_pr.set_title("Solidity Precision-Recall Curves across Feature Ablations", fontweight="bold")
    ax_pr.set_xlabel("Recall")
    ax_pr.set_ylabel("Precision")
    ax_pr.legend()
    ax_pr.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("d:/my_research/research/solidity_combined_roc_pr_curves.png", dpi=300)
    plt.close()
    print("[+] Generated real ROC/PR curves: d:/my_research/research/solidity_combined_roc_pr_curves.png")

    # Generate F1 & Accuracy Bar Chart
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(ablation_configs))
    w = 0.35
    accs = [eval_dict[m]["Accuracy (%)"] for m, _ in ablation_configs]
    f1s = [eval_dict[m]["Macro F1-Score (%)"] for m, _ in ablation_configs]
    ax.bar(x - w/2, accs, w, label="Accuracy (%)", color="#1f77b4")
    ax.bar(x + w/2, f1s, w, label="Macro F1-Score (%)", color="#aec7e8")
    ax.set_xticks(x)
    ax.set_xticklabels([m for m, _ in ablation_configs], rotation=15)
    ax.set_ylim(40, 100)
    ax.set_ylabel("Score (%)")
    ax.set_title("Solidity Feature Ablation: Accuracy vs Macro F1-Score", fontweight="bold")
    for i, (a, f) in enumerate(zip(accs, f1s)):
        ax.text(i - w/2, a + 1, f"{a:.1f}%", ha="center", fontsize=9, fontweight="bold")
        ax.text(i + w/2, f + 1, f"{f:.1f}%", ha="center", fontsize=9, fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig("d:/my_research/research/solidity_f1_accuracy_multibar.png", dpi=300)
    plt.close()
    print("[+] Generated real F1/Accuracy bar chart: d:/my_research/research/solidity_f1_accuracy_multibar.png")

    print("\n" + "=" * 80)
    print("SOLIDITY REALISTIC PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    main()
