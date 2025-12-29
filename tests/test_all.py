from unittest import mock
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import IsolationForest

import baseline_training
import drift_detection
import feature_extraction as fe
import repo_utils

# --------------------------
# Tests for feature extraction
# --------------------------


def test_extract_security_group_features():
    cfg = {
        "ingress": [{"cidr_blocks": ["0.0.0.0/0"], "from_port": 22, "to_port": 22, "protocol": "tcp"}],
        "egress": [{"cidr_blocks": ["10.0.0.0/16"]}],
    }
    features = fe.extract_security_group_features(cfg)
    assert features["ingress_rule_count"] == 1
    assert features["egress_rule_count"] == 1
    assert features["public_ingress_count"] == 1
    assert features["allows_ssh"] is True
    assert features["allows_all_ports"] is False
    assert features["protocol_any"] is False


def test_extract_s3_bucket_features():
    cfg = {
        "acl": "public-read",
        "versioning": [{"enabled": True}],
        "server_side_encryption_configuration": {"rule": {}},
        "public_access_block": {
            "block_public_acls": 1,
            "block_public_policy": 0,
            "ignore_public_acls": 1,
            "restrict_public_buckets": 0,
        },
    }
    features = fe.extract_s3_bucket_features(cfg)
    assert features["acl_public"] == 1
    assert features["versioning_enabled"] == 1
    assert features["encryption_enabled"] == 1
    assert features["block_public_acls"] == 1
    assert features["block_public_policy"] == 0
    assert features["ignore_public_acls"] == 1
    assert features["restrict_public_buckets"] == 0


def test_extract_iam_role_features():
    cfg = {
        "assume_role_policy": {"Statement": [{"Principal": "*"}]},
        "managed_policy_arns": ["arn:aws:iam::aws:policy/AdministratorAccess"],
    }
    features = fe.extract_iam_role_features(cfg)
    assert features["has_admin_policy"] == 1
    assert features["policy_count"] == 1
    assert features["assume_role_any_principal"] == 1


def test_extract_features_dispatcher():
    sg = fe.extract_features("aws_security_group", {"ingress": [], "egress": []})
    s3 = fe.extract_features("aws_s3_bucket", {"acl": "private"})
    iam = fe.extract_features("aws_iam_role", {"managed_policy_arns": []})
    unknown = fe.extract_features("aws_unknown", {})
    assert isinstance(sg, dict)
    assert isinstance(s3, dict)
    assert isinstance(iam, dict)
    assert unknown == {}


# --------------------------
# Tests for repo_utils
# --------------------------


@mock.patch("repo_utils.git.Repo.clone_from")
def test_clone_repo_at_sha(mock_clone):
    dest = "temp_repo"
    mock_repo = mock.Mock()
    mock_repo.git.checkout = mock.Mock()
    mock_clone.return_value = mock_repo
    ret = repo_utils.clone_repo_at_sha("https://fake.repo", "abc123", dest)
    assert ret == dest
    mock_repo.git.checkout.assert_called_with("abc123")


@mock.patch("builtins.open", new_callable=mock.mock_open, read_data="resource data")
@mock.patch("repo_utils.os.walk")
@mock.patch("repo_utils.hcl2.load")
def test_scan_repo(mock_hcl_load, mock_walk, mock_file):
    mock_walk.return_value = [("dir", (), ["file.tf"])]
    mock_hcl_load.return_value = {"resource": [{"aws_s3_bucket": {"mybucket": {"acl": "private"}}}]}

    resources = repo_utils.scan_repo("dir", fe.extract_features)
    assert any(r.startswith("aws_s3_bucket::") for r in resources.keys())


# --------------------------
# Tests for baseline_training.prepare_matrix
# --------------------------
def test_prepare_matrix_baseline():
    resources = {"r1": {"features": {"a": 1, "b": 2}}, "r2": {"features": {"b": 3, "c": 4}}}
    X, rids, fnames = baseline_training.prepare_matrix(resources)
    assert X.shape == (2, 3)  # 2 resources, 3 unique features
    assert set(fnames) == {"a", "b", "c"}
    assert rids == ["r1", "r2"]


# --------------------------
# Tests for drift_detection.prepare_matrix
# --------------------------
def test_prepare_matrix_drift():
    resources = {"r1": {"features": {"a": 1, "b": 2}}, "r2": {"features": {"b": 3, "c": 4}}}
    feature_names = ["a", "b", "c"]
    X, rids = drift_detection.prepare_matrix(resources, feature_names)
    assert X.shape == (2, 3)
    assert rids == ["r1", "r2"]


# --------------------------
# Test training and scaling pipeline
# --------------------------
def test_training_pipeline():
    resources = {"r1": {"features": {"a": 1, "b": 2}}, "r2": {"features": {"b": 3, "c": 4}}}
    X, rids, fnames = baseline_training.prepare_matrix(resources)
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    model = IsolationForest(random_state=42)
    model.fit(X_scaled)
    preds = model.predict(X_scaled)
    assert len(preds) == 2
