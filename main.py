import hcl2
import joblib
import numpy as np
import tensorflow as tf
import argparse
import os

ANOMALY_THRESHOLD = 0.1


def load_artifacts():
    print("Loading model and vectorizer...")
    try:
        # Load the saved model
        model = tf.keras.models.load_model("tf_security_model.h5")
        # Load the saved dictionary mapper
        vec = joblib.load("vectorizer.pkl")
        return model, vec
    except Exception as e:
        print(f"Error loading artifacts: {e}")
        print("Did you run train_model.py first?")
        exit()


def parse_terraform_file(filepath):
    """
    Parses a single .tf file and flattens the resources.
    Must match the logic used in the data loader exactly.
    """
    with open(filepath, "r") as file:
        try:
            dict_data = hcl2.load(file)
            resources = []
            if "resource" in dict_data:
                for entry in dict_data["resource"]:
                    for res_type, res_name_obj in entry.items():
                        for res_name, res_props in res_name_obj.items():
                            # Flatten structure
                            flat_resource = {"resource_type": res_type, "resource_name": res_name}
                            flat_resource.update(res_props)
                            resources.append(flat_resource)
            return resources
        except Exception as e:
            print(f"Failed to parse {filepath}: {e}")
            return []


def scan_file(filepath, model, vec):
    print(f"\n--- Scanning File: {filepath} ---")

    # 1. Parse the new file
    resources = parse_terraform_file(filepath)
    if not resources:
        print("No resources found or file is empty.")
        return

    # 2. Vectorize
    try:
        X_input = vec.transform(resources)
    except Exception as e:
        print(f"Vectorization error: {e}")
        return

    # 3. Predict (Reconstruct)
    reconstructions = model.predict(X_input, verbose=0)

    # 4. Calculate Loss (Mean Squared Error)
    mse = np.mean(np.power(X_input - reconstructions, 2), axis=1)

    # 5. Report Results
    anomalies_found = False
    print(f"\n{'RESOURCE':<40} | {'STATUS':<10} | {'LOSS SCORE'}")
    print("-" * 70)

    for i, error in enumerate(mse):
        res_name = resources[i].get("resource_name", "unknown")
        res_type = resources[i].get("resource_type", "unknown")
        full_name = f"{res_type}.{res_name}"

        if error > ANOMALY_THRESHOLD:
            anomalies_found = True
            status = "ANOMALY"
            print(f"{full_name:<40} | {status:<10} | {error:.5f} (High Risk!)")
        else:
            status = "OK"
            print(f"{full_name:<40} | {status:<10} | {error:.5f}")

    if anomalies_found:
        print("\n[!] ALERT: Anomalous infrastructure patterns detected.")
    else:
        print("\n[+] PASS: Infrastructure looks consistent with baseline.")


if __name__ == "__main__":
    # Setup command line arguments
    parser = argparse.ArgumentParser(description="Scan Terraform for anomalies")
    parser.add_argument("file", type=str, help="Path to the .tf file to scan")

    args = parser.parse_args()

    if os.path.exists(args.file):
        model, vec = load_artifacts()
        scan_file(args.file, model, vec)
    else:
        print(f"File not found: {args.file}")
