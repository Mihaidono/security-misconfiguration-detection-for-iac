import os
import json
import joblib
import numpy as np
from collections import defaultdict
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


def interpret_score(score):
    """Convert raw anomaly score to human-friendly description"""
    if score < -0.1:
        return "Highly unusual configuration"
    elif score < 0:
        return "Potential anomaly, review recommended"
    else:
        return "Configuration looks normal"


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

    # Build human-friendly interpreted report
    report_dict = defaultdict(lambda: {"count": 0, "items": []})
    anomalous_count = 0

    for i, rid in enumerate(resource_ids):
        score = float(scores[i])
        anomalous = bool(preds[i] == -1)
        if anomalous:
            anomalous_count += 1

        type_group = report_dict[resources[rid]["type"]]
        type_group["count"] += 1
        type_group["items"].append(
            {
                "name": rid.split("::")[-1],
                "file": resources[rid]["file"],
                "anomalous": anomalous,
                "score": round(score, 3),
                "interpretation": interpret_score(score),
            }
        )

    final_report = {
        "summary": {"total_resources": len(resources), "anomalous_count": anomalous_count},
        "resources": [{"type": t, **data} for t, data in report_dict.items()],
    }

    with open(args.output, "w") as f:
        json.dump(final_report, f, indent=2)

    print(f"Generated report for {len(resources)} resources ({anomalous_count} anomalous)")
    for t, data in report_dict.items():
        print(f"\n{t} ({data['count']} resources):")
        for item in data["items"]:
            status = "ANOMALY" if item["anomalous"] else "OK"
            print(f"  - {item['name']} [{item['file']}]: {status} ({item['interpretation']})")

    shutil.rmtree(repo_path, ignore_errors=True)
