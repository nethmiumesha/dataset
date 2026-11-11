import os
import sys
import re
import copy
import json
import random
import zipfile
import base64
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx

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

# Strict scientific seed initialization
def seed_everything(seed=42):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

seed_everything(42)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[+] Execution Device: {DEVICE}")
if DEVICE.type == "cuda":
    print(f"[+] Active GPU: {torch.cuda.get_device_name(0)}")
else:
    print("[!] GPU not detected; running in CPU fallback mode.")

# ==============================================================================
# VYPER 12-D FEATURE EXTRACTION SCHEMA
# ==============================================================================
FEATURE_NAMES = [
    "F0_normalized_length",
    "F1_branching_complexity",
    "F2_functional_scope",
    "F3_entry_visibility",
    "F4_critical_hooks",
    "F5_invariant_guards",
    "F6_arithmetic_channels",
    "F7_state_mutations",
    "F8_EVM_domain_flag",
    "F9_Sealevel_domain_flag",
    "F10_Pythonic_domain_flag",
    "F11_context_root_hub_flag"
]

def extract_vyper_12d_features(chunk_code, full_contract_low, is_hub=False):
    lines = chunk_code.splitlines()
    c_low = chunk_code.lower()

    # F0 (Normalized Length): min(Lines / 60.0, 1.0)
    f0_len = min(len(lines) / 60.0, 1.0)

    # F1 (Branching Complexity): Decision density -> min(Count / 5.0, 1.0)
    branch_count = len(re.findall(r"\b(?:if|elif|else|for|while|assert|raise)\b", c_low))
    f1_branch = min(branch_count / 5.0, 1.0)

    # F2 (Functional Scope): 1.0 if function definition or interface
    f2_scope = float(bool(re.search(r"\b(?:def\s+|@external|@internal|@deploy|@view|@pure|@nonreentrant|interface\s+)\b", c_low)))

    # F3 (Entry Visibility): 1.0 if public, external, deploy
    f3_vis = float(bool(re.search(r"\b(?:@external|@payable|@deploy|public\s*\()\b", c_low)))

    # F4 (Critical Execution Hooks): low-level external transfers / calls
    f4_hook = float(bool(re.search(r"\b(?:raw_call|send|selfdestruct)\b", c_low)))

    # F5 (Invariant Guards): security assertions / nonreentrant locks
    f5_guard = float(bool(re.search(r"\b(?:assert\b|raise\b|@nonreentrant|nonreentrant)\b", c_low)))

    # F6 (Arithmetic Channels): unsafe arithmetic operations
    has_unsafe_arith = bool(re.search(r"\b(?:unsafe_add|unsafe_sub|unsafe_mul|unsafe_div)\b", c_low))
    has_arith = bool(re.search(r"(?<![=<>!])(?:\+|\-|\*|\/)(?![=<>])", c_low))
    f6_arith = 1.0 if (has_unsafe_arith or ("unsafe" in c_low and has_arith)) else 0.0

    # F7 (State Mutations): assignment operator '=' or '+=' on storage/hashmaps
    f7_mutate = float(bool(re.search(r"(?<![=!<>])=(?![=])|\+=|-=|\*=", c_low)))

    # F8-F10: Domain Markers (EVM + Pythonic EVM for Vyper)
    f8_evm = 1.0
    f9_sealevel = 0.0
    f10_pythonic = 1.0

    # F11: Root Context Hub Flag
    f11_hub = 1.0 if is_hub else 0.0

    return [
        f0_len, f1_branch, f2_scope, f3_vis, f4_hook, f5_guard,
        f6_arith, f7_mutate, f8_evm, f9_sealevel, f10_pythonic, f11_hub
    ]

def parse_vyper_code(content):
    """Deconstructs a Vyper file into functional execution blocks (AST/CFG nodes)."""
    blocks = re.split(
        r"(?m)(?=^\s*(?:@external|@internal|@deploy|@view|@pure|@nonreentrant|def\s+|interface\s+)\b)",
        content
    )
    chunks = [b.strip() for b in blocks if b.strip() and len(b.strip()) > 8]
    if not chunks:
        chunks = [content.strip() or "# empty"]
    return chunks

def synthesize_single_file_graph(content, file_path):
    """Synthesizes a PyG Data object for a single-file Vyper contract."""
    chunks = parse_vyper_code(content)
    full_low = content.lower()
    features = []

    for i, c in enumerate(chunks):
        is_hub = (i == 0)
        feat = extract_vyper_12d_features(c, full_low, is_hub=is_hub)
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
    data.is_folderwise = False
    return data

def synthesize_folderwise_project_graph(file_dict, project_path):
    """Synthesizes a unified multi-contract project graph for a Folder_Wise repository."""
    combined_code = "\n".join(file_dict.values())
    combined_low = combined_code.lower()
    total_lines = sum(len(c.splitlines()) for c in file_dict.values())

    hub_chunk = f"# Project Root Hub\n# Total Contracts: {len(file_dict)}\n# Total Lines: {total_lines}\n"
    hub_feat = extract_vyper_12d_features(hub_chunk, combined_low, is_hub=True)

    features = [hub_feat]
    edges = []
    current_node_idx = 1

    for fname, code in file_dict.items():
        file_chunks = parse_vyper_code(code)
        file_low = code.lower()
        file_node_indices = []

        for chunk in file_chunks:
            feat = extract_vyper_12d_features(chunk, file_low, is_hub=False)
            features.append(feat)
            file_node_indices.append(current_node_idx)
            current_node_idx += 1

        for j in range(len(file_node_indices) - 1):
            u, v = file_node_indices[j], file_node_indices[j + 1]
            edges.extend([(u, v), (v, u)])

        for u in file_node_indices:
            edges.extend([(0, u), (u, 0)])

    if len(features) == 1:
        edges.append((0, 0))

    x = torch.tensor(features, dtype=torch.float32)
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    data = Data(x=x, edge_index=edge_index)
    data.file_path = project_path
    data.is_folderwise = True
    return data

# ==============================================================================
# GNN MODEL ARCHITECTURE
# ==============================================================================
class OptimizedVyperGNN(nn.Module):
    def __init__(self, in_channels, hidden_channels=64, num_classes=2):
        super(OptimizedVyperGNN, self).__init__()

        self.input_proj = nn.Linear(in_channels, hidden_channels)

        # Layer 1: GATv2 Attention Layer (4 attention heads, dropout=0.08)
        self.gat = GATv2Conv(hidden_channels, hidden_channels, heads=4, concat=False, dropout=0.08)
        self.ln1 = nn.LayerNorm(hidden_channels)

        # Layer 2: Graph Isomorphism Network (1-WL expressiveness) with 2-layer MLP
        gin_mlp = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels),
            nn.BatchNorm1d(hidden_channels),
            nn.GELU(),
            nn.Linear(hidden_channels, hidden_channels)
        )
        self.gin = GINConv(gin_mlp)
        self.ln2 = nn.LayerNorm(hidden_channels)

        # Hierarchical Readout & Latent Projection
        self.fc_pool = nn.Linear(hidden_channels * 2, 64)
        self.fc_latent = nn.Linear(64, 32)
        self.dropout = nn.Dropout(0.20)

        # Binary Classification Head
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

def slice_vyper_features(batch_x, mode):
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

def main():
    print("=" * 80)
    print("DEDICATED VYPER GNN PIPELINE (STRUCTURAL ANALYSIS PATH)")
    print("=" * 80)

    # 1. Dataset Scan
    DATASET_ROOT = "dataset/Vyper"
    if not os.path.exists(DATASET_ROOT):
        # Extract from dataset_vyper.zip if not extracted
        if os.path.exists("dataset_vyper.zip"):
            print("[*] Extracting dataset_vyper.zip...")
            with zipfile.ZipFile("dataset_vyper.zip", "r") as z:
                z.extractall("dataset")

    all_vy_paths = []
    for root, _, files in os.walk(DATASET_ROOT):
        for f in files:
            if f.lower().endswith(".vy"):
                all_vy_paths.append(os.path.join(root, f))

    print(f"[+] Total raw Vyper files located: {len(all_vy_paths)}")

    single_file_records = []
    folderwise_projects = defaultdict(lambda: {"label": None, "files": {}})

    for fpath in all_vy_paths:
        rel = os.path.relpath(fpath, DATASET_ROOT).replace(os.sep, "/")
        rel_low = rel.lower()

        is_safe = "safe" in rel_low or "clean" in rel_low
        is_vuln = "vuln" in rel_low or "unsafe" in rel_low
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
                if any(part.startswith(prefix) for prefix in ["safe_project_", "vuln_project_", "proj_"]):
                    proj_dir = "/".join(parts[:i + 1])
                    break
            if proj_dir is None:
                if len(parts) >= 3 and parts[-2].lower() in ["contracts", "helpers", "interfaces", "modules", "src"]:
                    proj_dir = "/".join(parts[:-2])
                else:
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

    print(f"[+] Categorized Single File candidates: {len(single_file_records)}")
    print(f"[+] Categorized Folder-Wise project candidates: {len(folderwise_projects)}")

    # Synthesize PyG Graphs
    vyper_graphs = []
    print("[*] Synthesizing Single File graphs...")
    for fpath, label in single_file_records:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if not content.strip():
                continue
            data = synthesize_single_file_graph(content, fpath)
            data.y = torch.tensor([label], dtype=torch.long)
            vyper_graphs.append(data)
        except Exception:
            continue

    print("[*] Synthesizing Folder-Wise unified project graphs...")
    for pdir, pdata in folderwise_projects.items():
        try:
            files = pdata["files"]
            label = pdata["label"]
            if not files or label is None:
                continue
            data = synthesize_folderwise_project_graph(files, pdir)
            data.y = torch.tensor([label], dtype=torch.long)
            vyper_graphs.append(data)
        except Exception:
            continue

    total_graphs = len(vyper_graphs)
    safe_count = sum(1 for g in vyper_graphs if g.y.item() == 0)
    vuln_count = sum(1 for g in vyper_graphs if g.y.item() == 1)
    single_count = sum(1 for g in vyper_graphs if not g.is_folderwise)
    folder_count = sum(1 for g in vyper_graphs if g.is_folderwise)

    print("=" * 80)
    print(f"[+] Multi-Level Graph Synthesis Complete:")
    print(f"    Total Synthesized Graphs : {total_graphs}")
    print(f"    - Safe Contracts (0)     : {safe_count} ({(safe_count/max(total_graphs,1))*100:.1f}%)")
    print(f"    - Vulnerable Contracts (1): {vuln_count} ({(vuln_count/max(total_graphs,1))*100:.1f}%)")
    print(f"    - Single-File Graphs     : {single_count}")
    print(f"    - Unified Project Graphs : {folder_count}")
    print("=" * 80)

    # 12-D Feature Variation Diagnostic
    all_feats = torch.cat([g.x for g in vyper_graphs], dim=0).cpu().numpy()
    print("12-D Feature Variation Diagnostic across all nodes:")
    print(f"{'Feature':<30} | {'Mean':<8} | {'Std':<8} | {'Min':<6} | {'Max':<6} | {'Unique Values'}")
    print("-" * 80)
    for i, name in enumerate(FEATURE_NAMES):
        col = all_feats[:, i]
        print(f"{name:<30} | {np.mean(col):<8.4f} | {np.std(col):<8.4f} | {np.min(col):<6.2f} | {np.max(col):<6.2f} | {len(np.unique(col))}")
    print("=" * 80)

    # Stratified Split (80/10/10)
    labels = [int(g.y.item()) for g in vyper_graphs]
    train_g, holdout_g = train_test_split(
        vyper_graphs, test_size=0.20, random_state=42, stratify=labels
    )
    holdout_labels = [int(g.y.item()) for g in holdout_g]
    val_g, test_g = train_test_split(
        holdout_g, test_size=0.50, random_state=42, stratify=holdout_labels
    )

    print(f"[+] Stratified Data Split Summary:")
    print(f"    Train Graphs : {len(train_g)} (Safe: {sum(1 for g in train_g if g.y.item()==0)}, Vuln: {sum(1 for g in train_g if g.y.item()==1)})")
    print(f"    Val Graphs   : {len(val_g)} (Safe: {sum(1 for g in val_g if g.y.item()==0)}, Vuln: {sum(1 for g in val_g if g.y.item()==1)})")
    print(f"    Test Graphs  : {len(test_g)} (Safe: {sum(1 for g in test_g if g.y.item()==0)}, Vuln: {sum(1 for g in test_g if g.y.item()==1)})")

    train_loader = DataLoader(train_g, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_g, batch_size=64, shuffle=False)
    test_loader = DataLoader(test_g, batch_size=64, shuffle=False)

    def collect_probabilities_and_targets(model, loader, mode):
        model.eval()
        probs_list = []
        targets_list = []
        with torch.no_grad():
            for batch in loader:
                batch = batch.to(DEVICE)
                x_in = slice_vyper_features(batch.x, mode)
                logits, _ = model(x_in, batch.edge_index, batch.batch)
                probs = F.softmax(logits, dim=1)[:, 1]
                probs_list.extend(probs.cpu().numpy())
                targets_list.extend(batch.y.cpu().numpy())
        return np.asarray(probs_list), np.asarray(targets_list)

    def train_and_evaluate_ablation_model(mode_name, in_channels, epochs=45):
        print(f"\n{'=' * 75}")
        print(f"TRAINING ABLATION CONFIGURATION: [{mode_name.upper()}] (in_channels = {in_channels})")
        print(f"{'=' * 75}")

        model = OptimizedVyperGNN(in_channels=in_channels, hidden_channels=64, num_classes=2).to(DEVICE)
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=3
        )
        criterion = nn.CrossEntropyLoss()

        best_val_loss = float("inf")
        best_weights = None
        patience, no_improve_count = 8, 0

        for epoch in range(1, epochs + 1):
            model.train()
            train_loss_total = 0.0
            for batch in train_loader:
                batch = batch.to(DEVICE)
                x_in = slice_vyper_features(batch.x, mode_name)
                optimizer.zero_grad()
                logits, _ = model(x_in, batch.edge_index, batch.batch)
                loss = criterion(logits, batch.y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
                optimizer.step()
                train_loss_total += loss.item() * batch.num_graphs

            # Validation
            model.eval()
            val_loss_total = 0.0
            with torch.no_grad():
                for batch in val_loader:
                    batch = batch.to(DEVICE)
                    x_in = slice_vyper_features(batch.x, mode_name)
                    logits, _ = model(x_in, batch.edge_index, batch.batch)
                    loss = criterion(logits, batch.y)
                    val_loss_total += loss.item() * batch.num_graphs

            avg_train_loss = train_loss_total / len(train_g)
            avg_val_loss = val_loss_total / len(val_g)
            scheduler.step(avg_val_loss)

            if avg_val_loss < best_val_loss - 1e-4:
                best_val_loss = avg_val_loss
                best_weights = copy.deepcopy(model.state_dict())
                no_improve_count = 0
            else:
                no_improve_count += 1

            if epoch == 1 or epoch % 5 == 0 or no_improve_count >= patience:
                print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")

            if no_improve_count >= patience:
                print(f"  [!] Early stopping triggered at epoch {epoch}.")
                break

        model.load_state_dict(best_weights)

        # Dynamic Threshold Calibration
        val_probs, val_targets = collect_probabilities_and_targets(model, val_loader, mode_name)
        precisions, recalls, pr_thresholds = precision_recall_curve(val_targets, val_probs)
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-8)
        best_f1_idx = int(np.argmax(f1_scores))
        if best_f1_idx < len(pr_thresholds):
            optimal_th = float(pr_thresholds[best_f1_idx])
        else:
            optimal_th = 0.50
        optimal_th = float(np.clip(optimal_th, 0.40, 0.60))

        # Test Set Evaluation
        test_probs, test_targets = collect_probabilities_and_targets(model, test_loader, mode_name)
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

        print(f"  [+] Optimal Validation Calibrated Threshold: {optimal_th:.4f}")
        print(f"  [+] Test Metrics -> Acc: {test_acc:.2f}% | BalAcc: {bal_acc:.2f}% | Prec: {prec:.2f}% | Rec: {rec:.2f}% | F1: {f1:.2f}% | ROC-AUC: {roc_auc:.4f}")
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
    trained_models_dict = {}
    evaluation_artifacts_dict = {}

    for mode, dim in ablation_configs:
        result_dict = train_and_evaluate_ablation_model(mode, dim, epochs=45)
        benchmark_records.append({k: v for k, v in result_dict.items() if k not in ["Targets", "Predictions", "Probabilities", "Model", "Confusion_Matrix"]})
        trained_models_dict[mode] = result_dict["Model"]
        evaluation_artifacts_dict[mode] = result_dict

    df_benchmark = pd.DataFrame(benchmark_records)
    print("\n" + "=" * 100)
    print("VYPER FEATURE-ABLATION BENCHMARK RESULTS")
    print("=" * 100)
    print(df_benchmark.to_string(index=False))
    df_benchmark.to_csv("vyper_feature_ablation_benchmark.csv", index=False)
    print("[+] Exported metrics to 'vyper_feature_ablation_benchmark.csv'")

    # --------------------------------------------------------------------------
    # PLOT 1: 4-PANEL CONFUSION MATRICES
    # --------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.2), dpi=160)
    for idx, (mode, dim) in enumerate(ablation_configs):
        cm = evaluation_artifacts_dict[mode]["Confusion_Matrix"]
        acc = evaluation_artifacts_dict[mode]["Accuracy (%)"]
        rec = evaluation_artifacts_dict[mode]["Recall / Sensitivity (%)"]
        th = evaluation_artifacts_dict[mode]["Optimal Calibrated Threshold"]

        sns.heatmap(cm, annot=True, fmt="d", cmap="Purples", cbar=False,
                    xticklabels=["Safe (0)", "Vuln (1)"],
                    yticklabels=["Safe (0)", "Vuln (1)"],
                    ax=axes[idx], annot_kws={"fontsize": 11, "fontweight": "bold"})
        axes[idx].set_title(f"{mode} ({dim}D)\nAcc: {acc:.2f}% | Rec: {rec:.2f}% | Th: {th:.2f}",
                            fontsize=10, fontweight="bold")
        axes[idx].set_xlabel("Predicted Class", fontsize=9)
        axes[idx].set_ylabel("Ground Truth Class", fontsize=9)

    plt.suptitle("Vyper GNN: 4-Panel Authenticated Confusion Matrices", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig("vyper_4panel_confusion_matrices.png", dpi=300, bbox_inches="tight")
    plt.close()

    # --------------------------------------------------------------------------
    # PLOT 2: MULTI-BAR F1 & ACCURACY CHART
    # --------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=160)
    x_idx = np.arange(len(ablation_configs))
    bar_width = 0.35

    acc_vals = [evaluation_artifacts_dict[m]["Accuracy (%)"] for m, _ in ablation_configs]
    f1_vals = [evaluation_artifacts_dict[m]["Macro F1-Score (%)"] for m, _ in ablation_configs]

    b1 = ax.bar(x_idx - bar_width/2, acc_vals, width=bar_width, label="Accuracy (%)", color="#756bb1", edgecolor="black", linewidth=0.8)
    b2 = ax.bar(x_idx + bar_width/2, f1_vals, width=bar_width, label="Macro F1-Score (%)", color="#bcbddc", edgecolor="black", linewidth=0.8)

    ax.set_xticks(x_idx)
    ax.set_xticklabels([m for m, _ in ablation_configs], fontsize=10, fontweight="bold")
    ax.set_ylabel("Metric Score (%)", fontsize=11, fontweight="bold")
    ax.set_ylim(0, 115)
    ax.set_title("Vyper Feature Ablation: Accuracy & F1-Score Comparison", fontsize=12, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for bar in b1 + b2:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                    fontsize=8.5, fontweight="bold")

    plt.tight_layout()
    plt.savefig("vyper_f1_accuracy_multibar.png", dpi=300, bbox_inches="tight")
    plt.close()

    # --------------------------------------------------------------------------
    # PLOT 3: COMBINED ROC & PR CURVES
    # --------------------------------------------------------------------------
    fig, (ax_roc, ax_pr) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=160)
    colors = ["#4E79A7", "#E15759", "#76B7B2", "#59A14F"]

    for (mode, dim), color in zip(ablation_configs, colors):
        targets = evaluation_artifacts_dict[mode]["Targets"]
        probs = evaluation_artifacts_dict[mode]["Probabilities"]
        roc_score = evaluation_artifacts_dict[mode]["ROC-AUC Score"]
        pr_score = evaluation_artifacts_dict[mode]["PR-AUC (Average Precision)"]

        fpr, tpr, _ = roc_curve(targets, probs)
        ax_roc.plot(fpr, tpr, label=f"{mode} (AUC = {roc_score:.3f})", color=color, linewidth=2)

        precision_curve, recall_curve, _ = precision_recall_curve(targets, probs)
        ax_pr.plot(recall_curve, precision_curve, label=f"{mode} (AP = {pr_score:.3f})", color=color, linewidth=2)

    ax_roc.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random Guess (0.500)")
    ax_roc.set_title("Vyper Combined ROC-AUC Curves", fontsize=11, fontweight="bold")
    ax_roc.set_xlabel("False Positive Rate (FPR)", fontsize=10)
    ax_roc.set_ylabel("True Positive Rate (TPR)", fontsize=10)
    ax_roc.legend(loc="lower right", fontsize=9)
    ax_roc.grid(True, linestyle="--", alpha=0.4)

    ax_pr.set_title("Vyper Combined Precision-Recall Curves", fontsize=11, fontweight="bold")
    ax_pr.set_xlabel("Recall / Sensitivity", fontsize=10)
    ax_pr.set_ylabel("Precision", fontsize=10)
    ax_pr.legend(loc="lower left", fontsize=9)
    ax_pr.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig("vyper_combined_roc_pr_curves.png", dpi=300, bbox_inches="tight")
    plt.close()

    # --------------------------------------------------------------------------
    # CELL 07: STANDALONE CONTRACT AUDITOR, 32-D EMBEDDING EXPORT & CFG PLOT
    # --------------------------------------------------------------------------
    sample_audit_target = "dataset/Vyper/safe/folderless/safe_contract_100000.vy"
    if not os.path.exists(sample_audit_target):
        sample_audit_target = single_file_records[0][0]

    with open(sample_audit_target, "r", encoding="utf-8") as f:
        target_code = f.read()

    audit_graph = synthesize_single_file_graph(target_code, sample_audit_target)
    combined_model = trained_models_dict["Combined 12D"]
    combined_th = evaluation_artifacts_dict["Combined 12D"]["Optimal Calibrated Threshold"]

    combined_model.eval()
    with torch.no_grad():
        x_in = audit_graph.x.to(DEVICE)
        edge_index_in = audit_graph.edge_index.to(DEVICE)
        batch_dummy = torch.zeros(audit_graph.x.size(0), dtype=torch.long, device=DEVICE)
        logits, h_struct_32 = combined_model(x_in, edge_index_in, batch_dummy)
        vuln_prob = F.softmax(logits, dim=1)[0, 1].item()
        is_vuln_pred = bool(vuln_prob >= combined_th)

    verdict_text = "⚠️ VULNERABLE CONTRACT DETECTED" if is_vuln_pred else "✅ SECURE CONTRACT IDENTIFIED"
    print("\n" + "=" * 80)
    print(f"AUDITING VYPER CONTRACT: {os.path.basename(sample_audit_target)}")
    print("=" * 80)
    print(f"Verdict                   : {verdict_text}")
    print(f"Vulnerability Confidence : {vuln_prob * 100:.2f}% (Decision Threshold = {combined_th * 100:.1f}%)")
    print(f"Safety Confidence        : {(1.0 - vuln_prob) * 100:.2f}%")
    print(f"Total Structural Nodes   : {audit_graph.x.size(0)} functional execution blocks")
    print(f"Total Graph Edges        : {audit_graph.edge_index.size(1)} control-flow / context connections")

    torch.save(h_struct_32.cpu(), "vyper_structural_embedding.pt")
    print(f"\n[+] Successfully exported 32-D Structural Embedding tensor:")
    print(f"    File  : 'vyper_structural_embedding.pt'")
    print(f"    Shape : {h_struct_32.shape} (H_struct in R^32)")

    # CFG Visualization
    G = nx.Graph()
    for i in range(audit_graph.x.size(0)):
        G.add_node(i)
    edge_list = audit_graph.edge_index.t().cpu().numpy()
    for u, v in edge_list:
        if u != v:
            G.add_edge(u, v)

    plt.figure(figsize=(7, 6), dpi=160)
    pos = nx.spring_layout(G, seed=42)
    node_colors = ["#e41a1c" if i == 0 else "#377eb8" for i in range(audit_graph.x.size(0))]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=600, edgecolors="black", linewidths=1.2)
    nx.draw_networkx_edges(G, pos, edge_color="gray", width=1.5, alpha=0.7)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold", font_color="white")
    plt.title(f"Vyper Control Flow Graph (CFG): {os.path.basename(sample_audit_target)}\n{verdict_text}", fontsize=11, fontweight="bold")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig("vyper_audited_graph.png", dpi=300, bbox_inches="tight")
    plt.close()

    print("[+] All publication-quality plots rendered and saved successfully.")

if __name__ == "__main__":
    main()
