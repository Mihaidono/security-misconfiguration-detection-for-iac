import os
import json
import joblib
import numpy as np
from repo_utils import clone_repo_at_sha, scan_repo
from feature_extraction import extract_features
import shutil


def prepare_matrix(resources, feature_names):
    resource_ids = []
    X = []
    for rid, rdata in resources.items():
        resource_ids.append(rid)
        row = [float(rdata["features"].get(f, 0)) for f in feature_names]
        X.append(row)
    return np.array(X, dtype=float), resource_ids


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--model-dir", default="models")
    parser.add_argument("--output", default="reports/drift_report.json")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Load baseline model, scaler, and feature names
    model = joblib.load(os.path.join(args.model_dir, "baseline_model.pkl"))
    scaler = joblib.load(os.path.join(args.model_dir, "scaler.pkl"))
    feature_names = joblib.load(os.path.join(args.model_dir, "feature_names.pkl"))

    # Clone repo and extract features
    repo_path = clone_repo_at_sha(args.repo, args.sha, os.path.join("temp_repo"))
    resources = scan_repo(repo_path, extract_features)

    # Prepare matrix using baseline features
    X, resource_ids = prepare_matrix(resources, feature_names)
    X_scaled = scaler.transform(X)

    # Compute anomaly scores
    scores = model.decision_function(X_scaled)
    preds = model.predict(X_scaled)

    # Generate human-readable report
    report = []
    for i, rid in enumerate(resource_ids):
        report.append(
            {
                "resource_id": str(rid),
                "type": resources[rid]["type"],
                "file": resources[rid]["file"],
                "anomaly_score": float(scores[i]),
                "anomalous": bool(preds[i] == -1),
            }
        )

    # Save report
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Generated report for {len(report)} resources at {args.output}")

    shutil.rmtree(repo_path, ignore_errors=True)
