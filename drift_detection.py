import os
import json
import joblib
import numpy as np
from repo_utils import clone_repo_at_sha, scan_repo
from feature_extraction import extract_features


def prepare_matrix(resources):
    rids = []
    X = []
    for rid, r in resources.items():
        rids.append(rid)
        row = [int(v) if isinstance(v, bool) else float(v) for v in r["features"].values()]
        X.append(row)
    return np.array(X), rids, list(resources[rids[0]]["features"].keys()) if rids else []


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--model-dir", default="models")
    parser.add_argument("--output", default="reports/drift_report.json")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    model = joblib.load(os.path.join(args.model_dir, "baseline_model.pkl"))
    scaler = joblib.load(os.path.join(args.model_dir, "scaler.pkl"))

    repo_path = clone_repo_at_sha(args.repo, args.sha, os.path.join("temp_repo"))
    resources = scan_repo(repo_path, extract_features)
    X, rids, feature_names = prepare_matrix(resources)
    X_scaled = scaler.transform(X)

    scores = model.decision_function(X_scaled)
    preds = model.predict(X_scaled)

    report = []
    for i, rid in enumerate(rids):
        report.append(
            {
                "resource_id": rid,
                "type": resources[rid]["type"],
                "file": resources[rid]["file"],
                "anomaly_score": float(scores[i]),
                "anomalous": preds[i] == -1,
            }
        )

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Generated report for {len(report)} resources at {args.output}")
