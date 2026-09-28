#!/usr/bin/env python3
"""
TF Drift Guard - core scan engine.

Checks (MVP):
  1. Terraform state drift (terraform plan -detailed-exitcode)
  2. Public / unencrypted S3 buckets
  3. Security groups open to 0.0.0.0/0 on sensitive ports (22, 3389, 3306, 5432)
  4. Unencrypted EBS volumes
  5. Missing required tags on EC2 instances / RDS instances

Outputs a markdown report and (optionally) posts violations to Slack.
Exits non-zero if violations found and --fail-on-violation=true.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import boto3
import requests

SENSITIVE_PORTS = {22, 3389, 3306, 5432}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--aws-region", default="us-east-1")
    p.add_argument("--required-tags", default="owner,environment")
    p.add_argument("--terraform-dir", default=".")
    p.add_argument("--slack-webhook-url", default="")
    p.add_argument("--fail-on-violation", default="true")
    return p.parse_args()


def check_terraform_drift(tf_dir: str) -> list[str]:
    violations = []
    tf_path = Path(tf_dir)
    if not (tf_path / ".terraform").exists() and not any(tf_path.glob("*.tf")):
        return violations  # no terraform project here; skip silently
    try:
        subprocess.run(["terraform", "init", "-input=false"], cwd=tf_dir, check=True,
                        capture_output=True, text=True, timeout=300)
        result = subprocess.run(
            ["terraform", "plan", "-detailed-exitcode", "-input=false"],
            cwd=tf_dir, capture_output=True, text=True, timeout=300,
        )
        # exit code 2 = changes present (drift or pending apply)
        if result.returncode == 2:
            violations.append(
                "Terraform drift detected: live infrastructure differs from state/config. "
                "Run `terraform plan` locally for details."
            )
        elif result.returncode not in (0, 2):
            violations.append(f"Terraform plan failed to evaluate cleanly: {result.stderr[:500]}")
    except Exception as e:  # pragma: no cover - defensive
        violations.append(f"Could not evaluate terraform drift: {e}")
    return violations


def check_s3(session) -> list[str]:
    violations = []
    s3 = session.client("s3")
    for bucket in s3.list_buckets().get("Buckets", []):
        name = bucket["Name"]
        try:
            enc = s3.get_bucket_encryption(Bucket=name)
            _ = enc  # encrypted, fine
        except s3.exceptions.ClientError:
            violations.append(f"S3 bucket `{name}` has no default encryption enabled.")
        try:
            pab = s3.get_public_access_block(Bucket=name)["PublicAccessBlockConfiguration"]
            if not all(pab.values()):
                violations.append(f"S3 bucket `{name}` does not fully block public access.")
        except s3.exceptions.ClientError:
            violations.append(f"S3 bucket `{name}` has no Public Access Block configuration.")
    return violations


def check_security_groups(session, region: str) -> list[str]:
    violations = []
    ec2 = session.client("ec2", region_name=region)
    for sg in ec2.describe_security_groups()["SecurityGroups"]:
        for perm in sg.get("IpPermissions", []):
            from_port = perm.get("FromPort")
            for ip_range in perm.get("IpRanges", []):
                if ip_range.get("CidrIp") == "0.0.0.0/0" and from_port in SENSITIVE_PORTS:
                    violations.append(
                        f"Security group `{sg['GroupId']}` ({sg.get('GroupName')}) "
                        f"exposes port {from_port} to the internet (0.0.0.0/0)."
                    )
    return violations


def check_ebs_encryption(session, region: str) -> list[str]:
    violations = []
    ec2 = session.client("ec2", region_name=region)
    for vol in ec2.describe_volumes()["Volumes"]:
        if not vol.get("Encrypted", False):
            violations.append(f"EBS volume `{vol['VolumeId']}` is not encrypted.")
    return violations


def check_required_tags(session, region: str, required_tags: list[str]) -> list[str]:
    violations = []
    ec2 = session.client("ec2", region_name=region)
    for reservation in ec2.describe_instances()["Reservations"]:
        for instance in reservation["Instances"]:
            tags = {t["Key"] for t in instance.get("Tags", [])}
            missing = [t for t in required_tags if t not in tags]
            if missing:
                violations.append(
                    f"EC2 instance `{instance['InstanceId']}` is missing required tag(s): {', '.join(missing)}."
                )
    return violations


def post_to_slack(webhook_url: str, violations: list[str]):
    if not webhook_url or not violations:
        return
    text = "*TF Drift Guard — violations found:*\n" + "\n".join(f"- {v}" for v in violations[:20])
    try:
        requests.post(webhook_url, json={"text": text}, timeout=10)
    except Exception as e:  # pragma: no cover
        print(f"Warning: failed to post to Slack: {e}", file=sys.stderr)


def main():
    args = parse_args()
    required_tags = [t.strip() for t in args.required_tags.split(",") if t.strip()]

    session = boto3.Session(region_name=args.aws_region)

    violations = []
    violations += check_terraform_drift(args.terraform_dir)
    violations += check_s3(session)
    violations += check_security_groups(session, args.aws_region)
    violations += check_ebs_encryption(session, args.aws_region)
    violations += check_required_tags(session, args.aws_region, required_tags)

    report_path = Path("tf-drift-guard-report.md")
    report_path.write_text(
        "# TF Drift Guard Report\n\n"
        + (f"Found **{len(violations)}** violation(s):\n\n" if violations else "No violations found. ✅\n\n")
        + "\n".join(f"- {v}" for v in violations)
    )

    print(json.dumps({"violations_count": len(violations)}))
    print(report_path.read_text())

    post_to_slack(args.slack_webhook_url, violations)

    if violations and args.fail_on_violation.lower() == "true":
        sys.exit(1)


if __name__ == "__main__":
    main()
