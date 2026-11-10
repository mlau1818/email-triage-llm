"""
Evaluate the triage system against the labeled datasets.

Usage:
    python evaluate.py                      # both datasets
    python evaluate.py --datasets data/emails_handwritten.csv
    python evaluate.py --limit 30           # quick run on the first 30 emails

Outputs (folder results/):
    predictions_<dataset>.csv   one row per email with predictions and labels
    confusion_<dataset>.png     confusion matrix for the category
    metrics.json                all metrics
"""
import argparse
import json
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             ConfusionMatrixDisplay, f1_score)

from triage import CATEGORY_DESCRIPTIONS, EmailTriage

CATEGORIES = list(CATEGORY_DESCRIPTIONS.keys())


def join(values):
    return ";".join(values)


def evaluate_file(path, triage, limit=None, out_dir="results"):
    name = os.path.splitext(os.path.basename(path))[0]
    df = pd.read_csv(path).fillna("")
    if limit:
        df = df.head(limit)

    start = time.time()
    preds = triage.triage_batch(df["email_text"].tolist())
    elapsed = time.time() - start

    out = df.copy()
    out["pred_category"] = [p["category"] for p in preds]
    out["pred_urgency"] = [p["urgency"] for p in preds]
    out["pred_urgency_model_only"] = [p["urgency_model"] for p in preds]
    out["urgency_source"] = [p["urgency_source"] for p in preds]
    out["pred_requester"] = [p["requester"] for p in preds]
    out["pred_due_date"] = [p["due_date"] for p in preds]
    out["pred_amounts"] = [join(p["amounts"]) for p in preds]
    out["pred_ids"] = [join(p["ids"]) for p in preds]
    out["pred_summary"] = [p["summary"] for p in preds]
    out["pred_tasks"] = [join(p["tasks"]) for p in preds]
    os.makedirs(out_dir, exist_ok=True)
    out.to_csv(os.path.join(out_dir, f"predictions_{name}.csv"), index=False)

    metrics = {
        "n_emails": len(df),
        "seconds_total": round(elapsed, 1),
        "category_accuracy": accuracy_score(out["category"], out["pred_category"]),
        "category_macro_f1": f1_score(out["category"], out["pred_category"],
                                      labels=CATEGORIES, average="macro", zero_division=0),
        "urgency_accuracy_hybrid": accuracy_score(out["urgency"], out["pred_urgency"]),
        "urgency_accuracy_model_only": accuracy_score(out["urgency"],
                                                      out["pred_urgency_model_only"]),
        "requester_exact_match": (out["requester"] == out["pred_requester"]).mean(),
        "due_date_exact_match": (out["due_date"].str.lower()
                                 == out["pred_due_date"].str.lower()).mean(),
        "amounts_exact_match": (out["amounts"] == out["pred_amounts"]).mean(),
        "ids_exact_match": (out["ids"] == out["pred_ids"]).mean(),
    }
    metrics = {k: round(float(v), 3) if isinstance(v, float) else v for k, v in metrics.items()}

    print(f"\n===== {name} ({len(df)} emails, {elapsed:.0f}s) =====")
    for k, v in metrics.items():
        print(f"  {k:30s} {v}")
    print("\nCategory report:")
    print(classification_report(out["category"], out["pred_category"],
                                labels=CATEGORIES, zero_division=0))

    cm = confusion_matrix(out["category"], out["pred_category"], labels=CATEGORIES)
    fig, ax = plt.subplots(figsize=(8, 7))
    ConfusionMatrixDisplay(cm, display_labels=CATEGORIES).plot(ax=ax, xticks_rotation=45,
                                                               colorbar=False, cmap="Blues")
    ax.set_title(f"Category confusion matrix - {name}")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, f"confusion_{name}.png"), dpi=150)
    plt.close(fig)
    return name, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+",
                        default=["data/emails.csv", "data/emails_handwritten.csv"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out_dir", default="results")
    args = parser.parse_args()

    print("Loading models (first run downloads them, ~2 GB)...")
    triage = EmailTriage(urgency_mode="hybrid")
    all_metrics = {}
    for path in args.datasets:
        name, m = evaluate_file(path, triage, args.limit, args.out_dir)
        all_metrics[name] = m
    with open(os.path.join(args.out_dir, "metrics.json"), "w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\nSaved predictions, confusion matrices and metrics.json in {args.out_dir}/")


if __name__ == "__main__":
    main()
