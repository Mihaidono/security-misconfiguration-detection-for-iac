import os
import git
import hcl2
import pickle
from datetime import datetime

# --- CONFIGURATION ---
# These are "Gold Standard" repos known to have high-quality, secure code.
REPO_URLS = [
    "https://github.com/terraform-aws-modules/terraform-aws-vpc.git",
    "https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git",
    "https://github.com/terraform-aws-modules/terraform-aws-security-group.git",
    "https://github.com/terraform-aws-modules/terraform-aws-rds.git",
    "https://github.com/terraform-aws-modules/terraform-aws-ec2-instance.git",
    # Add more official modules here to make your model smarter
]

DATA_DIR = "./temp_training_data"
OUTPUT_FILE = "./temp_training_data/training_data.pkl"


def flatten_json(y):
    """Turns nested JSON into flat features (context-aware)."""
    out = {}

    def flatten(x, name=""):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], name + a + "_")
        elif isinstance(x, list):
            for i, a in enumerate(x):
                flatten(a, name + str(i) + "_")
        else:
            if isinstance(x, bool):
                x = 1 if x else 0
            out[name[:-1]] = x

    flatten(y)
    return out


def download_repos():
    """Clones or pulls the latest version of the repos."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    print(f"🔄 Syncing {len(REPO_URLS)} repositories...")

    for url in REPO_URLS:
        repo_name = url.split("/")[-1].replace(".git", "")
        repo_path = os.path.join(DATA_DIR, repo_name)

        if os.path.exists(repo_path):
            print(f"   - Updating {repo_name}...")
            try:
                repo = git.Repo(repo_path)
                repo.remotes.origin.pull()
            except Exception as e:
                print(f"     ⚠️ Could not update {repo_name}: {e}")
        else:
            print(f"   - Cloning {repo_name}...")
            git.Repo.clone_from(url, repo_path)


def parse_files():
    """Walks through the downloaded repos and extracts resource blocks."""
    print("🔍 Parsing Terraform files...")
    dataset = []

    # Walk through every folder in our temp data directory
    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith(".tf"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        data = hcl2.load(f)

                        # Extract Resources
                        if "resource" in data:
                            for res_type_dict in data["resource"]:
                                for res_type, instances in res_type_dict.items():
                                    for res_name, config in instances.items():
                                        # Flatten immediately
                                        flat = flatten_json(config)
                                        flat["resource_type"] = res_type  # Critical feature
                                        dataset.append(flat)

                except Exception as e:
                    # Terraform files often have syntax errors or unsupported HCL features
                    # We skip them to keep the dataset clean
                    pass

    print(f"✅ Extracted {len(dataset)} resource blocks.")
    return dataset


def main():
    start_time = datetime.now()

    # 1. Download/Update Code
    download_repos()

    # 2. Parse into Data
    data = parse_files()

    # 3. Save as Pickle (faster than CSV for nested structures)
    if data:
        with open(OUTPUT_FILE, "wb") as f:
            pickle.dump(data, f)
        print(f"💾 Saved training data to {OUTPUT_FILE}")
        print(f"⏱️  Total time: {datetime.now() - start_time}")
    else:
        print("⚠️ No data found. Check internet connection or repo URLs.")


if __name__ == "__main__":
    main()
