# TF Drift Guard

A lightweight Terraform / AWS drift & security-compliance guardrail.

Detects (MVP scope):
- Terraform state drift (`terraform plan -detailed-exitcode`)
- Public S3 buckets / missing encryption
- Security groups open to 0.0.0.0/0 on sensitive ports
- Unencrypted EBS volumes
- Missing required tags (e.g. `owner`, `environment`, `cost-center`)

Distribution model:
- **Free**: GitHub Action — run in CI, comment on PRs, fail build on violation.
- **Free**: Terraform module — deploys a scheduled Lambda that runs the same
  checks against live AWS accounts and posts to Slack/PagerDuty.
- **Paid (Pro)**: Hosted multi-account dashboard + historical trends + SSO,
  sold as a SaaS Contract on AWS Marketplace.

## Repo layout
```
action.yml              # GitHub Action definition (Docker-based)
Dockerfile              # Container image for the action
scan.py                 # Core scan logic (boto3 + terraform CLI)
requirements.txt
terraform-module/       # `terraform-aws-drift-guard` — deploys scheduled Lambda
helm-chart/             # Kyverno policy bundle for the same checks inside EKS
.github/workflows/      # CI to build/test/release this project itself
```

## Quick start (as a GitHub Action consumer)
```yaml
- uses: your-org/tf-drift-guard@v1
  with:
    aws-region: us-east-1
    required-tags: "owner,environment,cost-center"
    slack-webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
```
