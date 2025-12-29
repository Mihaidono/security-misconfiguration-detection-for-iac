import os
import joblib
import numpy as np
from collections import defaultdict
from repo_utils import clone_repo_at_sha, scan_repo
from feature_extraction import extract_features
import shutil
from colorama import Fore, Style, init

init(autoreset=True)  # ensures colors reset after each line


def prepare_matrix(resources, feature_names):
    resource_ids = []
    X = []
    for rid, rdata in resources.items():
        resource_ids.append(rid)
        row = [float(rdata["features"].get(f, 0)) for f in feature_names]
        X.append(row)
    return np.array(X, dtype=float), resource_ids


def interpret_score(score):
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
    args = parser.parse_args()

    # Load baseline model
    model = joblib.load(os.path.join(args.model_dir, "baseline_model.pkl"))
    scaler = joblib.load(os.path.join(args.model_dir, "scaler.pkl"))
    feature_names = joblib.load(os.path.join(args.model_dir, "feature_names.pkl"))

    # Clone repo and extract features
    repo_path = clone_repo_at_sha(args.repo, args.sha, os.path.join("temp_repo"))
    resources = scan_repo(repo_path, extract_features)

    # Prepare matrix
    X, resource_ids = prepare_matrix(resources, feature_names)
    X_scaled = scaler.transform(X)

    scores = model.decision_function(X_scaled)
    preds = model.predict(X_scaled)

    # Group by resource type
    report_dict = defaultdict(list)
    anomalous_count = 0
    for i, rid in enumerate(resource_ids):
        score = float(scores[i])
        anomalous = bool(preds[i] == -1)
        if anomalous:
            anomalous_count += 1
        report_dict[resources[rid]["type"]].append(
            {
                "name": rid.split("::")[-1],
                "file": resources[rid]["file"],
                "anomalous": anomalous,
                "interpretation": interpret_score(score),
            }
        )

    # Print formatted and colored report
    print(f"{Fore.CYAN}=== Drift Report ==={Style.RESET_ALL}")
    print(f"Total Resources: {len(resources)}")
    print(f"Anomalous Resources: {anomalous_count}\n")

    for rtype, items in report_dict.items():
        print(f"{Fore.MAGENTA}[{rtype}] ({len(items)} resources){Style.RESET_ALL}")
        for item in items:
            if item["anomalous"]:
                color = Fore.RED
                status = "ANOMALY"
            elif "Potential anomaly" in item["interpretation"]:
                color = Fore.YELLOW
                status = "WARNING"
            else:
                color = Fore.GREEN
                status = "OK"

            print(f"  - {item['name']} ({item['file']}): {color}{status}{Style.RESET_ALL} → {item['interpretation']}")
        print("")

    shutil.rmtree(repo_path, ignore_errors=True)
