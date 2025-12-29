import os
import git
import hcl2


def clone_repo_at_sha(repo_url, sha, dest_dir):
    if os.path.exists(dest_dir):
        repo = git.Repo(dest_dir)
        repo.remotes.origin.fetch()
    else:
        repo = git.Repo.clone_from(repo_url, dest_dir)
    repo.git.checkout(sha)
    return dest_dir


def scan_repo(repo_root, feature_extractor):
    """Walk repo and extract features per resource."""
    resources = {}
    for dirpath, _, filenames in os.walk(repo_root):
        for fname in filenames:
            if not fname.endswith(".tf"):
                continue
            path = os.path.join(dirpath, fname)
            try:
                with open(path) as f:
                    data = hcl2.load(f)
            except Exception:
                continue
            if "resource" not in data:
                continue
            for block in data["resource"]:
                for rtype, instances in block.items():
                    for name, config in instances.items():
                        module_path = os.path.relpath(path, repo_root)
                        rid = f"{rtype}::{module_path}::{name}"
                        features = feature_extractor(rtype, config)
                        resources[rid] = {
                            "type": rtype,
                            "features": features,
                            "file": module_path,
                        }
    return resources
