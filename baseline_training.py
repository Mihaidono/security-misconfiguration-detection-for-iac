import os
import joblib
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import IsolationForest
from repo_utils import clone_repo_at_sha, scan_repo
from feature_extraction import extract_features
import shutil


def prepare_matrix(resources):
    all_keys = set()
    for r in resources.values():
        all_keys.update(r["features"].keys())
    all_keys = sorted(all_keys)

    X = []
    rids = []
    for rid, rdata in resources.items():
        row = [rdata["features"].get(k, 0) for k in all_keys]
        X.append(row)
        rids.append(rid)

    return np.array(X, dtype=float), rids, all_keys


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--model-dir", default="models")
    args = parser.parse_args()

    os.makedirs(args.model_dir, exist_ok=True)
    repo_path = clone_repo_at_sha(args.repo, args.sha, os.path.join("temp_repo"))

    resources = scan_repo(repo_path, extract_features)
    X, _, _ = prepare_matrix(resources)

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(X_scaled)

    joblib.dump(model, os.path.join(args.model_dir, "baseline_model.pkl"))
    joblib.dump(scaler, os.path.join(args.model_dir, "scaler.pkl"))

    print(f"Trained baseline model on {len(resources)} resources")

    shutil.rmtree(repo_path, ignore_errors=True)
