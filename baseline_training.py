import os
import joblib
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import IsolationForest
from repo_utils import clone_repo_at_sha, scan_repo
from feature_extraction import extract_features
import shutil


def prepare_matrix(resources):
    # Collect all unique feature names across resources
    feature_names = sorted({k for r in resources.values() for k in r["features"].keys()})

    X = []
    resource_ids = []
    for rid, rdata in resources.items():
        row = [float(rdata["features"].get(f, 0)) for f in feature_names]
        X.append(row)
        resource_ids.append(rid)

    return np.array(X, dtype=float), resource_ids, feature_names


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--model-dir", default="models")
    args = parser.parse_args()

    os.makedirs(args.model_dir, exist_ok=True)

    # Clone the repo at specific SHA
    repo_path = clone_repo_at_sha(args.repo, args.sha, os.path.join("temp_repo"))

    # Scan repo and extract features
    resources = scan_repo(repo_path, extract_features)

    # Prepare feature matrix
    X, resource_ids, feature_names = prepare_matrix(resources)

    # Scale features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    # Train Isolation Forest
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(X_scaled)

    # Save model, scaler, and feature names
    joblib.dump(model, os.path.join(args.model_dir, "baseline_model.pkl"))
    joblib.dump(scaler, os.path.join(args.model_dir, "scaler.pkl"))
    joblib.dump(feature_names, os.path.join(args.model_dir, "feature_names.pkl"))

    print(f"Trained baseline model on {len(resources)} resources")

    shutil.rmtree(repo_path, ignore_errors=True)
