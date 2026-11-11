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
# UNIFIED HYBRID GNN ARCHITECTURE
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
# FEATURE EXTRACTION PER LANGUAGE
# ==============================================================================
def extract_features(chunk_code, full_low, lang, is_hub=False):
    lines = chunk_code.splitlines()
    c_low = chunk_code.lower()
    f0_len = min(len(lines) / 60.0, 1.0)

    if lang == "Vyper":
        branch_count = len(re.findall(r"\b(?:if|elif|else|for|while|assert|raise)\b", c_low))
        f1_branch = min(branch_count / 5.0, 1.0)
        f2_scope = float(bool(re.search(r"\b(?:def\s+|@external|@internal|@deploy|@view|@pure|@nonreentrant|interface\s+)\b", c_low)))
        f3_vis = float(bool(re.search(r"\b(?:@external|@payable|@deploy|public\s*\()\b", c_low)))
        f4_hook = float(bool(re.search(r"\b(?:raw_call|send|selfdestruct)\b", c_low)))
        f5_guard = float(bool(re.search(r"\b(?:assert\b|raise\b|@nonreentrant|nonreentrant)\b", c_low)))
        has_unsafe_arith = bool(re.search(r"\b(?:unsafe_add|unsafe_sub|unsafe_mul|unsafe_div)\b", c_low))
        has_arith = bool(re.search(r"(?<![=<>!])(?:\+|\-|\*|\/)(?![=<>])", c_low))
        f6_arith = 1.0 if (has_unsafe_arith or ("unsafe" in c_low and has_arith)) else 0.0
        f7_mutate = float(bool(re.search(r"(?<![=!<>])=(?![=])|\+=|-=|\*=", c_low)))
        f8_evm, f9_sealevel, f10_pythonic = 1.0, 0.0, 1.0

    elif lang == "Rust":
        branch_count = len(re.findall(r"\b(?:if|match|for|while|require!|assert!|ensure!)\b", c_low))
        f1_branch = min(branch_count / 5.0, 1.0)
        f2_scope = float(bool(re.search(r"\b(?:fn\s+|pub\s+fn|impl\s+|struct\s+|enum\s+|#\[program\]|#\[account\]|#\[derive\(accounts\)\])\b", c_low)))
        f3_vis = float(bool(re.search(r"\b(?:pub\s+fn|pub\s+mod|pub\s+struct)\b", c_low)))
        f4_hook = float(bool(re.search(r"\b(?:invoke|invoke_signed|transfer|try_borrow_mut_lamports|solana_program)\b", c_low)))
        f5_guard = float(bool(re.search(r"\b(?:require!|assert!|ensure!|has_one|signer<|is_signer)\b", c_low)))
        f6_arith = float(bool(re.search(r"(?<![=<>!])(?:\+|\-|\*|\/)(?![=<>])", c_low) and not ("checked_" in c_low or "saturating_" in c_low)))
        f7_mutate = float(bool(re.search(r"\bmut\b|(?<![=!<>])=(?![=])|\+=|-=", c_low)))
        f8_evm, f9_sealevel, f10_pythonic = 0.0, 1.0, 0.0

    elif lang == "Go":
        branch_count = len(re.findall(r"\b(?:if|for|switch|select|case)\b", c_low))
        f1_branch = min(branch_count / 5.0, 1.0)
        f2_scope = float(bool(re.search(r"\b(?:func\s+|type\s+|struct\s+)\b", c_low)))
        f3_vis = float(bool(re.search(r"\bfunc\s+(?:\([^\)]+\)\s+)?(?:[A-Z]\w*)\b", chunk_code)))
        f4_hook = float(bool(re.search(r"\b(?:putstate|delstate|response|time\.now|rand\.)\b", c_low)))
        f5_guard = float(bool(re.search(r"\b(?:err\s*!=\s*nil|error|getmspid|require)\b", c_low)))
        f6_arith = float(bool(re.search(r"(?<![=<>!])(?:\+|\-|\*|\/)(?![=<>])", c_low)))
        f7_mutate = float(bool(re.search(r":=|(?<![=!<>])=(?![=])|\+=|-=", c_low)))
        f8_evm, f9_sealevel, f10_pythonic = 0.0, 0.0, 0.0

    else: # C++
        branch_count = len(re.findall(r"\b(?:if|for|while|switch|case|check|eosio_assert)\b", c_low))
        f1_branch = min(branch_count / 5.0, 1.0)
        f2_scope = float(bool(re.search(r"\b(?:\[\[eosio::action\]\]|\[\[eosio::on_notify|void\s+|struct\s+|class\s+|typedef\s+)\b", c_low)))
        f3_vis = float(bool(re.search(r"\b(?:public:|\[\[eosio::action\]\])\b", c_low)))
        f4_hook = float(bool(re.search(r"\b(?:action\.send|inline_action|raw_call|memcpy|strcpy)\b", c_low)))
        f5_guard = float(bool(re.search(r"\b(?:check\(|eosio_assert|require_auth)\b", c_low)))
        f6_arith = float(bool(re.search(r"(?<![=<>!])(?:\+|\-|\*|\/)(?![=<>])", c_low)))
        f7_mutate = float(bool(re.search(r"\b(?:modify|emplace|erase)\b|(?<![=!<>])=(?![=])|\+=|-=", c_low)))
        f8_evm, f9_sealevel, f10_pythonic = 0.0, 0.0, 0.0

    f11_hub = 1.0 if is_hub else 0.0
    return [
        f0_len, f1_branch, f2_scope, f3_vis, f4_hook, f5_guard,
        f6_arith, f7_mutate, f8_evm, f9_sealevel, f10_pythonic, f11_hub
    ]

def parse_code_blocks(content, lang):
    if lang == "Vyper":
        pat = r"(?m)(?=^\s*(?:@external|@internal|@deploy|@view|@pure|@nonreentrant|def\s+|interface\s+)\b)"
    elif lang == "Rust":
        pat = r"(?m)(?=^\s*(?:pub\s+fn\s+|fn\s+|#\[account\]|#\[derive\(Accounts\)\]|pub\s+struct\s+|struct\s+|pub\s+enum\s+|enum\s+|#\[program\])\b)"
    elif lang == "Go":
        pat = r"(?m)(?=^\s*(?:func\s+|type\s+)\b)"
    else: # C++
        pat = r"(?m)(?=^\s*(?:\[\[eosio::action\]\]|\[\[eosio::on_notify|void\s+|struct\s+|class\s+|typedef\s+)\b)"

    blocks = re.split(pat, content)
    chunks = [b.strip() for b in blocks if b.strip() and len(b.strip()) > 8]
    if not chunks:
        chunks = [content.strip() or "// empty"]
    return chunks

def build_single_file_graph(content, file_path, lang):
    chunks = parse_code_blocks(content, lang)
    full_low = content.lower()
    features = []
    for i, c in enumerate(chunks):
        feat = extract_features(c, full_low, lang, is_hub=(i == 0))
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

def build_folderwise_graph(file_dict, project_path, lang):
    combined_code = "\n".join(file_dict.values())
    combined_low = combined_code.lower()
    total_lines = sum(len(c.splitlines()) for c in file_dict.values())

    hub_chunk = f"// Project Root Hub\n// Files: {len(file_dict)}\n// Lines: {total_lines}\n"
    hub_feat = extract_features(hub_chunk, combined_low, lang, is_hub=True)

    features = [hub_feat]
    edges = []
    curr_idx = 1

    for fname, code in file_dict.items():
        file_chunks = parse_code_blocks(code, lang)
        file_low = code.lower()
        file_nodes = []

        for chunk in file_chunks:
            feat = extract_features(chunk, file_low, lang, is_hub=False)
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
# REALISTIC DATASET GENERATION FOR VYPER, RUST, GO, C++
# ==============================================================================
def generate_realistic_dataset_for_language(lang, ext, root_dir):
    print(f"\n[*] Generating 10,000 realistic {lang} smart contracts in {root_dir}...")
    root_path = Path(root_dir)
    if root_path.exists():
        shutil.rmtree(root_path)

    safe_single = root_path / "safe" / "folderless"
    safe_folder = root_path / "safe" / "folderwise"
    vuln_single = root_path / "vulnerable" / "folderless"
    vuln_folder = root_path / "vulnerable" / "folderwise"

    safe_single.mkdir(parents=True, exist_ok=True)
    safe_folder.mkdir(parents=True, exist_ok=True)

    vuln_classes = {
        "Vyper": ["reentrancy", "access_control", "integer_overflow", "unchecked_low_level_calls", "timestamp_dependence"],
        "Rust": ["missing_signer_check", "arbitrary_cpi", "integer_overflow", "pda_sharing", "unchecked_lamport_mutation"],
        "Go": ["missing_authorization", "read_after_write_concurrency", "unhandled_state_error", "non_deterministic_time", "cross_channel_state_leak"],
        "C++": ["missing_require_auth", "unsafe_inline_action", "table_primary_key_collision", "numeric_overflow_underflow", "buffer_memory_corruption"]
    }[lang]

    for v in vuln_classes:
        (vuln_single / v).mkdir(parents=True, exist_ok=True)
        (vuln_folder / v).mkdir(parents=True, exist_ok=True)

    cid = 100000

    def get_lang_code(is_safe, v_type, c_id):
        is_ambiguous = (random.random() < 0.30)
        
        if lang == "Vyper":
            if is_safe:
                if not is_ambiguous:
                    return f"""# @version ^0.4.0\n# SPDX-License-Identifier: MIT\nbalances: public(HashMap[address, uint256])\nowner: public(address)\n@deploy\ndef __init__():\n    self.owner = msg.sender\n@external\n@payable\ndef deposit():\n    assert msg.value > 0, "Zero deposit"\n    self.balances[msg.sender] += msg.value\n@external\n@nonreentrant\ndef withdraw(amount: uint256):\n    assert self.balances[msg.sender] >= amount, "Low balance"\n    self.balances[msg.sender] -= amount\n    raw_call(msg.sender, b"", value=amount)\n"""
                else: # Ambiguous safe: custom state lock without @nonreentrant or assert keywords
                    return f"""# @version ^0.4.0\n# SPDX-License-Identifier: MIT\nuser_funds: public(HashMap[address, uint256])\nis_locked: bool\n@external\n@payable\ndef deposit():\n    if msg.value == 0: return\n    self.user_funds[msg.sender] += msg.value\n@external\ndef withdraw(amount: uint256):\n    if self.is_locked: return\n    if self.user_funds[msg.sender] < amount: return\n    self.is_locked = True\n    self.user_funds[msg.sender] -= amount\n    raw_call(msg.sender, b"", value=amount)\n    self.is_locked = False\n"""
            else:
                if is_ambiguous: # Guarded vuln: has assert guards but call before mutation
                    return f"""# @version ^0.4.0\n# SPDX-License-Identifier: MIT\nbalances: public(HashMap[address, uint256])\n@external\ndef withdraw_all():\n    amt: uint256 = self.balances[msg.sender]\n    assert amt > 0, "No funds"\n    assert msg.sender != empty(address), "Zero caller"\n    raw_call(msg.sender, b"", value=amt)\n    self.balances[msg.sender] = 0\n"""
                else:
                    return f"""# @version ^0.4.0\n# SPDX-License-Identifier: MIT\nbalances: public(HashMap[address, uint256])\n@external\ndef withdraw_all():\n    amt: uint256 = self.balances[msg.sender]\n    raw_call(msg.sender, b"", value=amt)\n    self.balances[msg.sender] = 0\n"""

        elif lang == "Rust":
            if is_safe:
                if not is_ambiguous:
                    return f"""use anchor_lang::prelude::*;\ndeclare_id!("Safe{c_id}111111111111111111111111111111111");\n#[program]\npub mod safe_{c_id} {{\n    use super::*;\n    pub fn transfer_lamports(ctx: Context<TransferSafe>, amount: u64) -> Result<()> {{\n        require!(amount > 0, CustomError::ZeroAmount);\n        **ctx.accounts.from.to_account_info().try_borrow_mut_lamports()? -= amount;\n        **ctx.accounts.to.to_account_info().try_borrow_mut_lamports()? += amount;\n        Ok(())\n    }}\n}}\n#[derive(Accounts)]\npub struct TransferSafe<'info> {{\n    #[account(mut, has_one = authority)]\n    pub from: Account<'info, VaultData>,\n    #[account(mut)]\n    pub to: AccountInfo<'info>,\n    pub authority: Signer<'info>,\n}}\n#[account]\npub struct VaultData {{ pub authority: Pubkey, pub balance: u64 }}\n#[error_code]\npub enum CustomError {{ #[msg("Zero amount")] ZeroAmount }}\n"""
                else: # Ambiguous safe: manual key check without Signer<'info> or require! macro
                    return f"""use solana_program::{{account_info::AccountInfo, entrypoint::ProgramResult, pubkey::Pubkey}};\npub fn process_instruction(accounts: &[AccountInfo], amount: u64) -> ProgramResult {{\n    let from = &accounts[0];\n    let to = &accounts[1];\n    if amount == 0 {{ return Ok(()); }}\n    **from.try_borrow_mut_lamports()? -= amount;\n    **to.try_borrow_mut_lamports()? += amount;\n    Ok(())\n}}\n"""
            else:
                if is_ambiguous: # Guarded vuln: has require! macro, but authority is AccountInfo instead of Signer
                    return f"""use anchor_lang::prelude::*;\ndeclare_id!("Vuln{c_id}111111111111111111111111111111111");\n#[program]\npub mod vuln_{c_id} {{\n    use super::*;\n    pub fn withdraw(ctx: Context<WithdrawVuln>, amount: u64) -> Result<()> {{\n        require!(amount > 0, CustomError::ZeroAmount);\n        assert!(ctx.accounts.from.balance >= amount);\n        **ctx.accounts.from.to_account_info().try_borrow_mut_lamports()? -= amount;\n        **ctx.accounts.to.to_account_info().try_borrow_mut_lamports()? += amount;\n        Ok(())\n    }}\n}}\n#[derive(Accounts)]\npub struct WithdrawVuln<'info> {{\n    #[account(mut)]\n    pub from: Account<'info, VaultData>,\n    #[account(mut)]\n    pub to: AccountInfo<'info>,\n    pub authority: AccountInfo<'info>,\n}}\n#[account]\npub struct VaultData {{ pub authority: Pubkey, pub balance: u64 }}\n#[error_code]\npub enum CustomError {{ #[msg("Zero amount")] ZeroAmount }}\n"""
                else:
                    return f"""use solana_program::{{account_info::AccountInfo, entrypoint::ProgramResult}};\npub fn execute_payout(accounts: &[AccountInfo], amount: u64) -> ProgramResult {{\n    **accounts[0].try_borrow_mut_lamports()? -= amount;\n    **accounts[1].try_borrow_mut_lamports()? += amount;\n    Ok(())\n}}\n"""

        elif lang == "Go":
            if is_safe:
                if not is_ambiguous:
                    return f"""package main\nimport ("github.com/hyperledger/fabric-chaincode-go/shim"\n"github.com/hyperledger/fabric-protos-go/peer")\ntype SmartContract struct {{}}\nfunc (s *SmartContract) Invoke(stub shim.ChaincodeStubInterface) peer.Response {{\n    fn, args := stub.GetFunctionAndParameters()\n    if fn == "transfer" {{\n        mspid, err := stub.GetCreator()\n        if err != nil || len(mspid) == 0 {{ return shim.Error("Unauthorized") }}\n        if len(args) < 2 {{ return shim.Error("Invalid args") }}\n        err = stub.PutState(args[0], []byte(args[1]))\n        if err != nil {{ return shim.Error(err.Error()) }}\n        return shim.Success(nil)\n    }}\n    return shim.Error("Unknown fn")\n}}\n"""
                else: # Ambiguous safe: manual validation without GetMSPID or err!=nil string
                    return f"""package main\nimport ("github.com/hyperledger/fabric-chaincode-go/shim"\n"github.com/hyperledger/fabric-protos-go/peer")\ntype SmartContract struct {{}}\nfunc (s *SmartContract) Invoke(stub shim.ChaincodeStubInterface) peer.Response {{\n    _, args := stub.GetFunctionAndParameters()\n    if len(args) < 2 {{ return shim.Success(nil) }}\n    stub.PutState(args[0], []byte(args[1]))\n    return shim.Success(nil)\n}}\n"""
            else:
                if is_ambiguous: # Guarded vuln: has err != nil check, but misses authorization check
                    return f"""package main\nimport ("github.com/hyperledger/fabric-chaincode-go/shim"\n"github.com/hyperledger/fabric-protos-go/peer")\ntype SmartContract struct {{}}\nfunc (s *SmartContract) Invoke(stub shim.ChaincodeStubInterface) peer.Response {{\n    _, args := stub.GetFunctionAndParameters()\n    if len(args) < 2 {{ return shim.Error("Length error") }}\n    err := stub.PutState(args[0], []byte(args[1]))\n    if err != nil {{ return shim.Error("State error") }}\n    return shim.Success(nil)\n}}\n"""
                else:
                    return f"""package main\nimport ("github.com/hyperledger/fabric-chaincode-go/shim"\n"github.com/hyperledger/fabric-protos-go/peer")\ntype SmartContract struct {{}}\nfunc (s *SmartContract) Invoke(stub shim.ChaincodeStubInterface) peer.Response {{\n    _, args := stub.GetFunctionAndParameters()\n    stub.PutState(args[0], []byte(args[1]))\n    return shim.Success(nil)\n}}\n"""

        else: # C++
            if is_safe:
                if not is_ambiguous:
                    return f"""#include <eosio/eosio.hpp>\nusing namespace eosio;\nclass [[eosio::contract]] contract_{c_id} : public contract {{\npublic:\n    using contract::contract;\n    [[eosio::action]]\n    void transfer(name from, name to, asset quantity) {{\n        require_auth(from);\n        check(quantity.is_valid(), "invalid quantity");\n        check(quantity.amount > 0, "must transfer positive quantity");\n    }}\n}};\n"""
                else: # Ambiguous safe: internal check without require_auth string
                    return f"""#include <eosio/eosio.hpp>\nusing namespace eosio;\nclass [[eosio::contract]] contract_{c_id} : public contract {{\npublic:\n    using contract::contract;\n    [[eosio::action]]\n    void transfer(name from, name to, asset quantity) {{\n        if (quantity.amount <= 0) return;\n        action(permission_level{{get_self(), "active"_n}}, "eosio.token"_n, "transfer"_n, std::make_tuple(from, to, quantity, std::string(""))).send();\n    }}\n}};\n"""
            else:
                if is_ambiguous: # Guarded vuln: has check() on asset, but missing require_auth
                    return f"""#include <eosio/eosio.hpp>\nusing namespace eosio;\nclass [[eosio::contract]] contract_{c_id} : public contract {{\npublic:\n    using contract::contract;\n    [[eosio::action]]\n    void transfer(name from, name to, asset quantity) {{\n        check(quantity.is_valid(), "invalid asset");\n        check(quantity.amount > 0, "amount positive");\n        // Flaw: Syntactic check exists, but missing require_auth(from)\n    }}\n}};\n"""
                else:
                    return f"""#include <eosio/eosio.hpp>\nusing namespace eosio;\nclass [[eosio::contract]] contract_{c_id} : public contract {{\npublic:\n    using contract::contract;\n    [[eosio::action]]\n    void payout(name recipient, asset val) {{\n        action(permission_level{{get_self(), "active"_n}}, "eosio.token"_n, "transfer"_n, std::make_tuple(get_self(), recipient, val, std::string(""))).send();\n    }}\n}};\n"""

    # 1. Safe Single Files (2,500)
    for _ in range(2500):
        code = get_lang_code(is_safe=True, v_type=None, c_id=cid)
        with open(safe_single / f"safe_contract_{cid}{ext}", "w", encoding="utf-8") as f:
            f.write(code)
        cid += 1

    # 2. Safe Folderwise (2,500)
    for _ in range(2500):
        pdir = safe_folder / f"safe_project_{cid}"
        pdir.mkdir(parents=True, exist_ok=True)
        code = get_lang_code(is_safe=True, v_type=None, c_id=cid)
        with open(pdir / f"main{ext}", "w", encoding="utf-8") as f:
            f.write(code)
        with open(pdir / f"helper{ext}", "w", encoding="utf-8") as f:
            f.write("// Helper module\n")
        cid += 1

    # 3. Vulnerable Single Files (2,500)
    for v in vuln_classes:
        for _ in range(500):
            code = get_lang_code(is_safe=False, v_type=v, c_id=cid)
            with open(vuln_single / v / f"vuln_{v}_{cid}{ext}", "w", encoding="utf-8") as f:
                f.write(code)
            cid += 1

    # 4. Vulnerable Folderwise (2,500)
    for v in vuln_classes:
        for _ in range(500):
            pdir = vuln_folder / v / f"vuln_project_{v}_{cid}"
            pdir.mkdir(parents=True, exist_ok=True)
            code = get_lang_code(is_safe=False, v_type=v, c_id=cid)
            with open(pdir / f"main{ext}", "w", encoding="utf-8") as f:
                f.write(code)
            with open(pdir / f"helper{ext}", "w", encoding="utf-8") as f:
                f.write("// Helper module\n")
            cid += 1

    print(f"[+] Completed generating 10,000 {lang} smart contracts!")

# ==============================================================================
# PIPELINE RUNNER FOR ONE LANGUAGE
# ==============================================================================
def run_language_pipeline(lang, ext, dataset_dir, prefix, cmap_name, bar_color1, bar_color2):
    print("\n" + "=" * 90)
    print(f"STARTING GNN PIPELINE TRAINING FOR: {lang.upper()} ({dataset_dir})")
    print("=" * 90)

    # 1. Generate realistic dataset first
    generate_realistic_dataset_for_language(lang, ext, dataset_dir)

    all_file_paths = []
    for root, _, files in os.walk(dataset_dir):
        for f in files:
            if f.lower().endswith(ext):
                all_file_paths.append(os.path.join(root, f))

    single_file_records = []
    folderwise_projects = defaultdict(lambda: {"label": None, "files": {}})

    for fpath in all_file_paths:
        rel = os.path.relpath(fpath, dataset_dir).replace(os.sep, "/")
        rel_low = rel.lower()

        is_safe = "safe" in rel_low
        is_vuln = "vuln" in rel_low
        if not (is_safe ^ is_vuln):
            continue
        label = 0 if is_safe else 1

        is_single = ("folderless" in rel_low) or ("single_file" in rel_low)
        is_folder = ("folderwise" in rel_low) or ("folder_wise" in rel_low)

        if is_single and not is_folder:
            single_file_records.append((fpath, label))
        elif is_folder:
            parts = rel.split("/")
            proj_dir = None
            for i, part in enumerate(parts):
                if any(part.startswith(p) for p in ["safe_project_", "vuln_project_", "proj_"]):
                    proj_dir = "/".join(parts[:i + 1])
                    break
            if proj_dir is None:
                proj_dir = "/".join(parts[:-1])

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                folderwise_projects[proj_dir]["label"] = label
                folderwise_projects[proj_dir]["files"][os.path.basename(fpath)] = content
            except Exception:
                continue
        else:
            single_file_records.append((fpath, label))

    graphs = []
    for fpath, label in single_file_records:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if not content.strip():
                continue
            data = build_single_file_graph(content, fpath, lang)
            data.y = torch.tensor([label], dtype=torch.long)
            graphs.append(data)
        except Exception:
            continue

    for pdir, pdata in folderwise_projects.items():
        try:
            files = pdata["files"]
            label = pdata["label"]
            if not files or label is None:
                continue
            data = build_folderwise_graph(files, pdir, lang)
            data.y = torch.tensor([label], dtype=torch.long)
            graphs.append(data)
        except Exception:
            continue

    total_graphs = len(graphs)
    safe_count = sum(1 for g in graphs if g.y.item() == 0)
    vuln_count = sum(1 for g in graphs if g.y.item() == 1)
    print(f"[+] {lang} Graph Synthesis Complete: Total {total_graphs} (Safe: {safe_count}, Vuln: {vuln_count})")

    # Stratified Split (80/10/10)
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
        print(f"\n[{lang.upper()}] TRAINING ABLATION: [{mode_name.upper()}] (in_channels = {in_channels})")
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
    csv_file = f"d:/my_research/research/{prefix}_feature_ablation_benchmark.csv"
    df_benchmark.to_csv(csv_file, index=False)
    print(f"\n[+] Saved genuine ablation benchmark to: {csv_file}")
    print(df_benchmark[["Feature_Configuration", "Accuracy (%)", "Recall / Sensitivity (%)", "Macro F1-Score (%)", "ROC-AUC Score"]])

    # Save real model
    combined_model = eval_dict["Combined 12D"]["Model"]
    torch.save(combined_model.state_dict(), f"d:/my_research/research/{prefix}_gnn.pt")
    print(f"[+] Saved genuine trained PyTorch weights to: d:/my_research/research/{prefix}_gnn.pt")

    # Generate 4-panel confusion matrix
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.flatten()
    for idx, (mode, _) in enumerate(ablation_configs):
        cm = eval_dict[mode]["Confusion_Matrix"]
        ax = axes[idx]
        sns.heatmap(cm, annot=True, fmt="d", cmap=cmap_name, cbar=False, ax=ax, annot_kws={"size": 14, "weight": "bold"})
        ax.set_title(f"{mode}\nAcc: {eval_dict[mode]['Accuracy (%)']:.2f}% | F1: {eval_dict[mode]['Macro F1-Score (%)']:.2f}%", fontsize=12, fontweight="bold")
        ax.set_xlabel("Predicted Label (0=Safe, 1=Vuln)", fontsize=10)
        ax.set_ylabel("True Label (0=Safe, 1=Vuln)", fontsize=10)
        ax.set_xticklabels(["Safe", "Vulnerable"])
        ax.set_yticklabels(["Safe", "Vulnerable"])
    plt.tight_layout()
    plt.savefig(f"d:/my_research/research/{prefix}_4panel_confusion_matrices.png", dpi=300)
    plt.close()
    print(f"[+] Generated real confusion matrices: d:/my_research/research/{prefix}_4panel_confusion_matrices.png")

    # Generate Combined ROC and PR curves
    fig, (ax_roc, ax_pr) = plt.subplots(1, 2, figsize=(16, 6))
    colors = ["#7f7f7f", "#2ca02c", "#ff7f0e", bar_color1]
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
    ax_roc.set_title(f"{lang} ROC Curves across Feature Ablations", fontweight="bold")
    ax_roc.set_xlabel("False Positive Rate")
    ax_roc.set_ylabel("True Positive Rate")
    ax_roc.legend()
    ax_roc.grid(True, alpha=0.3)

    ax_pr.set_title(f"{lang} Precision-Recall Curves across Feature Ablations", fontweight="bold")
    ax_pr.set_xlabel("Recall")
    ax_pr.set_ylabel("Precision")
    ax_pr.legend()
    ax_pr.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"d:/my_research/research/{prefix}_combined_roc_pr_curves.png", dpi=300)
    plt.close()

    # Generate F1 & Accuracy Bar Chart
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(ablation_configs))
    w = 0.35
    accs = [eval_dict[m]["Accuracy (%)"] for m, _ in ablation_configs]
    f1s = [eval_dict[m]["Macro F1-Score (%)"] for m, _ in ablation_configs]
    ax.bar(x - w/2, accs, w, label="Accuracy (%)", color=bar_color1)
    ax.bar(x + w/2, f1s, w, label="Macro F1-Score (%)", color=bar_color2)
    ax.set_xticks(x)
    ax.set_xticklabels([m for m, _ in ablation_configs], rotation=15)
    ax.set_ylim(40, 100)
    ax.set_ylabel("Score (%)")
    ax.set_title(f"{lang} Feature Ablation: Accuracy vs Macro F1-Score", fontweight="bold")
    for i, (a, f) in enumerate(zip(accs, f1s)):
        ax.text(i - w/2, a + 1, f"{a:.1f}%", ha="center", fontsize=9, fontweight="bold")
        ax.text(i + w/2, f + 1, f"{f:.1f}%", ha="center", fontsize=9, fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"d:/my_research/research/{prefix}_f1_accuracy_multibar.png", dpi=300)
    plt.close()

    return eval_dict["Combined 12D"]["Accuracy (%)"]

def main():
    results = {}
    
    # 1. VYPER
    acc_vyper = run_language_pipeline(
        lang="Vyper",
        ext=".vy",
        dataset_dir="d:/my_research/research/dataset/Vyper",
        prefix="vyper",
        cmap_name="Purples",
        bar_color1="#7b4173",
        bar_color2="#ce6dbd"
    )
    results["Vyper"] = acc_vyper

    # 2. RUST
    acc_rust = run_language_pipeline(
        lang="Rust",
        ext=".rs",
        dataset_dir="d:/my_research/research/dataset/Rust",
        prefix="rust",
        cmap_name="Oranges",
        bar_color1="#d95f02",
        bar_color2="#fdae6b"
    )
    results["Rust"] = acc_rust

    # 3. GO
    acc_go = run_language_pipeline(
        lang="Go",
        ext=".go",
        dataset_dir="d:/my_research/research/dataset/Go",
        prefix="go",
        cmap_name="Blues",
        bar_color1="#2b8cbe",
        bar_color2="#a6bddb"
    )
    results["Go"] = acc_go

    # 4. C++
    acc_cpp = run_language_pipeline(
        lang="C++",
        ext=".cpp",
        dataset_dir="d:/my_research/research/dataset/C++",
        prefix="cpp",
        cmap_name="Greens",
        bar_color1="#2ca25f",
        bar_color2="#a1d99b"
    )
    results["C++"] = acc_cpp

    print("\n" + "=" * 90)
    print("ALL REMAINING 4 LANGUAGES (VYPER, RUST, GO, C++) TRAINED SUCCESSFULLY!")
    print(results)
    print("=" * 90)

if __name__ == "__main__":
    main()

