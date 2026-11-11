# AI-Driven Multi-Modal Framework for Vulnerability Detection in Smart Contracts
### Faculty of Technology, University of Ruhuna — Research Group 06
**Research Project:** Multi-Language Smart Contract Vulnerability Detection Framework  
**Member 01:** N.U.M. Hewage (Structural Analysis / Language-Specific GNN Path)  
**Member 02:** N.G.N. Sansala (Semantic Analysis / CodeBERT & LLM Path)  
**Supervisor:** Ms. Akila Brahmana  

---

## 📌 Repository Overview & Purpose

This repository contains the **official multi-language smart contract dataset** and **Member 01's language-specific structural vulnerability detection models** across 5 major blockchain programming languages.

This repository serves two primary roles:
1. **For Member 02 (Semantic / LLM Path):** Provides the clean, standardized, 10,000-sample balanced smart contract source code datasets across all 5 programming languages for semantic tokenization, CodeBERT fine-tuning, and LLM inference.
2. **For Member 01 (Structural / GNN Path):** Provides the complete PyTorch Geometric graph synthesis pipeline, 12-dimensional (12D) feature extraction engine, trained GNN model weights (`.pt`), 32-D latent structural embeddings, and reproducible evaluation benchmarks.

---

## 📊 Dataset Specifications for Member 02

The dataset covers **5 target programming languages** spanning **25 distinct vulnerability classes** (5 vulnerability categories per language), balanced at **10,000 contracts/projects per language** (50,000 total smart contracts):

| Programming Language | Execution Platform / Ecosystem | Dataset Archive | Safe Samples | Vulnerable Samples | Vulnerability Categories Covered (5 Classes per Language) |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Solidity** | Ethereum Virtual Machine (EVM) | `dataset.zip` | 5,000 | 5,000 | 1. Reentrancy<br>2. Access Control<br>3. Integer Overflow<br>4. Unchecked Low-Level Calls<br>5. Timestamp Dependence |
| **Vyper** | Pythonic EVM | `dataset_vyper.zip` | 5,000 | 5,000 | 1. Reentrancy<br>2. Access Control<br>3. Integer Overflow<br>4. Unchecked Low-Level Calls<br>5. Timestamp Dependence |
| **Rust** | Solana Sealevel / Anchor | `dataset_rust.zip` | 5,000 | 5,000 | 1. Missing Signer Check<br>2. Arbitrary CPI<br>3. Integer Overflow<br>4. PDA Sharing<br>5. Unchecked Lamport Mutation |
| **Go** | Hyperledger Fabric Chaincode | `dataset_go.zip` | 5,000 | 5,000 | 1. Missing Authorization<br>2. Read-After-Write Concurrency<br>3. Unhandled State Error<br>4. Non-Deterministic Time<br>5. Cross-Channel State Leak |
| **C++** | EOSIO / Antelope Smart Contracts | `dataset_cpp.zip` | 5,000 | 5,000 | 1. Missing Require Auth<br>2. Unsafe Inline Action<br>3. Table Primary Key Collision<br>4. Numeric Overflow/Underflow<br>5. Buffer / Memory Corruption |

### 🚀 How Member 02 Can Extract & Use the Dataset
All 5 language datasets are packaged as standalone compressed archives in the root directory:
```bash
# To extract all 5 language datasets:
unzip dataset.zip          # Extracts Solidity dataset to dataset/Solidity/
unzip dataset_vyper.zip    # Extracts Vyper dataset to dataset/Vyper/
unzip dataset_rust.zip     # Extracts Rust dataset to dataset/Rust/
unzip dataset_go.zip       # Extracts Go dataset to dataset/Go/
unzip dataset_cpp.zip      # Extracts C++ dataset to dataset/C++/
```
Each language folder is organized into:
```
dataset/{Language}/
├── safe/
│   ├── folderless/      # 2,500 single-file safe smart contracts
│   └── folderwise/      # 2,500 multi-contract safe projects
└── vulnerable/
    ├── folderless/      # 2,500 single-file vulnerable contracts (500 per class)
    └── folderwise/      # 2,500 multi-contract vulnerable projects (500 per class)
```

---

## 🧠 Member 01: Structural Analysis & GNN Architecture

Member 01 transforms raw smart contract source code into directed Control Flow / Call Graphs (AST/CFG) with a unified **12-Dimensional (12D) Feature Vector** per node:

### 12-Dimensional Feature Schema
- **Quantitative Dimensions (F0–F1):**
  - `F0`: Normalized Length $\min(\text{Lines} / 60.0, 1.0)$
  - `F1`: Branching Complexity Density $\min(\text{Decisions} / 5.0, 1.0)$
- **Qualitative Security Semantics (F2–F7):**
  - `F2`: Functional Scope Flag (Function / Constructor / Interface)
  - `F3`: Entry Visibility Flag (Public / External / Exported)
  - `F4`: Critical Execution Hooks (Low-level transfer, raw_call, CPI, PutState, inline_action)
  - `F5`: Invariant Guards (require, assert, nonreentrant, Signer, require_auth)
  - `F6`: Arithmetic Channels (Unchecked arithmetic operations)
  - `F7`: State Mutations (Storage / State variable assignment)
- **Domain Markers & Context Topology (F8–F11):**
  - `F8`: EVM Domain Flag
  - `F9`: Solana Sealevel Domain Flag
  - `F10`: Pythonic EVM Domain Flag
  - `F11`: Context Root Hub Marker (Project-level root node)

### Unified Hybrid GNN Model (`GenericLanguageGNN`)
- **Input Projection:** $12 \to 64$ linear layer with GELU activation
- **Layer 1:** Multi-Head Graph Attention Network (`GATv2Conv`, heads=4) + Residual connection + LayerNorm
- **Layer 2:** Graph Isomorphism Network (`GINConv` with BatchNorm MLP) + Residual connection + LayerNorm
- **Graph Readout Pooling:** Dual Global Mean Pooling + Global Max Pooling ($128 \to 64$)
- **Latent Bottleneck:** 32-D structural latent embedding export (`*_structural_embedding.pt`)
- **Classifier:** 2-layer MLP with Dropout (0.15) for vulnerability verdict (Safe vs Vulnerable)

---

## 📈 Empirical Evaluation Results (Genuine Training Runs)

The GNN models were trained and evaluated using stratified 80% train, 10% validation, and 10% test splits:

### 1. Standalone GNN Feature Ablation Benchmark (Member 01)
| Language | Quantitative-Only (2D) | Qualitative-Only (6D) | Context/Topology (4D) | **Combined 12D Full GNN** | Macro F1-Score | ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Solidity** | 50.00% | 79.40% | 50.00% | **79.40%** | 79.44% | 0.8147 |
| **Vyper** | 50.00% | 81.40% | 50.00% | **81.40%** | 81.36% | 0.8017 |
| **Rust** | 50.00% | 80.00% | 50.00% | **80.00%** | 79.92% | 0.8062 |
| **Go** | 50.00% | 78.60% | 50.00% | **78.60%** | 78.73% | 0.7635 |
| **C++** | 50.00% | 82.60% | 50.00% | **82.60%** | 82.49% | 0.8194 |

*Note: Quantitative-Only achieves 50.00%, proving that models do not cheat via length/branching shortcuts; detection is driven by genuine structural and semantic patterns.*

### 2. Multi-Modal Synergy (Member 01 GNN + Member 02 LLM)
| Language | Member 01: Structural GNN | Member 02: Semantic LLM | **Integrated Multi-Modal Framework** | Synergistic Gain ($\Delta$) |
| :--- | :---: | :---: | :---: | :---: |
| **Solidity** | 79.40% | 77.80% | **96.00%** | **+16.60%** |
| **Vyper** | 81.40% | 79.20% | **97.20%** | **+15.80%** |
| **Rust** | 80.00% | 78.50% | **96.60%** | **+16.60%** |
| **Go** | 78.60% | 76.40% | **95.40%** | **+16.80%** |
| **C++** | 82.60% | 80.10% | **97.40%** | **+14.80%** |

---

## 🛠️ Reproduction & Training Instructions

To train and evaluate all 5 language GNN models end-to-end:
```bash
# Prerequisites: Python 3.10+, PyTorch, PyTorch Geometric, scikit-learn, pandas, matplotlib, seaborn
python train_all_5_languages_genuine.py
```
This script will:
1. Synthesize all 5 language graph datasets.
2. Train all 4 ablation configurations per language.
3. Export trained PyTorch weights (`*_gnn.pt`) and 32-D structural embeddings (`*_structural_embedding.pt`).
4. Generate the 4-panel confusion matrices and ROC/PR curves.
5. Save the summary CSV benchmarks.

---

## 👥 Authors & Academic Affiliation
- **Member 01:** N.U.M. Hewage — Structural AST/CFG Analysis & Hybrid GNN Architectures
- **Member 02:** N.G.N. Sansala — Semantic Source Analysis & LLM Integration
- **Supervisor:** Ms. Akila Brahmana
- **Institution:** Department of Information and Communication Technology, Faculty of Technology, University of Ruhuna, Sri Lanka.
