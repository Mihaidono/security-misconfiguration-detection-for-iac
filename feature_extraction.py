def extract_security_group_features(config):
    ingress = config.get("ingress", [])
    egress = config.get("egress", [])

    def is_public(rule):
        return "0.0.0.0/0" in rule.get("cidr_blocks", [])

    def allows_port(rule, port):
        return rule.get("from_port") == port or rule.get("to_port") == port

    return {
        "ingress_rule_count": len(ingress),
        "egress_rule_count": len(egress),
        "public_ingress_count": sum(is_public(r) for r in ingress),
        "allows_ssh": any(allows_port(r, 22) for r in ingress),
        "allows_all_ports": any(r.get("from_port") == 0 and r.get("to_port") == 65535 for r in ingress),
        "protocol_any": any(r.get("protocol") == "-1" for r in ingress),
    }


def extract_s3_bucket_features(config):
    acl = config.get("acl", "")
    versioning = config.get("versioning", [{}])
    encryption = config.get("server_side_encryption_configuration", {})
    public_access_block = config.get("public_access_block", {})

    return {
        "acl_public": int(acl in ["public-read", "public-read-write"]),
        "versioning_enabled": int(versioning[0].get("enabled", False) if versioning else 0),
        "encryption_enabled": int(bool(encryption)),
        "block_public_acls": int(public_access_block.get("block_public_acls", 0)),
        "block_public_policy": int(public_access_block.get("block_public_policy", 0)),
        "ignore_public_acls": int(public_access_block.get("ignore_public_acls", 0)),
        "restrict_public_buckets": int(public_access_block.get("restrict_public_buckets", 0)),
    }


def extract_iam_role_features(config):
    assume_role_policy = config.get("assume_role_policy", {})
    managed_policies = config.get("managed_policy_arns", [])

    return {
        "has_admin_policy": int(any("AdministratorAccess" in p for p in managed_policies)),
        "policy_count": len(managed_policies),
        "assume_role_any_principal": int("*" in str(assume_role_policy)),
    }


def extract_features(rtype, config):
    """Main dispatcher to extract features per resource type."""
    if rtype == "aws_security_group":
        return extract_security_group_features(config)
    elif rtype == "aws_s3_bucket":
        return extract_s3_bucket_features(config)
    elif rtype == "aws_iam_role":
        return extract_iam_role_features(config)
    else:
        return {}
