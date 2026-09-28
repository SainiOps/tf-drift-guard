# TF Drift Guard

[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-TF%20Drift%20Guard-blue?logo=github)](https://github.com/marketplace/actions/tf-drift-guard)
[![Terraform Registry](https://img.shields.io/badge/Terraform%20Registry-SainiOps%2Fdrift--guard%2Faws-844FBA?logo=terraform)](https://registry.terraform.io/modules/SainiOps/drift-guard/aws)
[![Artifact Hub](https://img.shields.io/badge/Artifact%20Hub-Kyverno%20Policies-417598?logo=kubernetes)](https://artifacthub.io/packages/search?repo=tf-drift-guard-kyverno-policies)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Catch Terraform drift and AWS security/compliance violations before they
reach production — in CI, on a schedule, or inside your EKS cluster.**

No agents to install, no account to create, no sales call. Add one line to
your CI pipeline (or one Terraform module, or one Helm-style policy) and it
starts reporting immediately.

## What it catches
- **Terraform state drift** — live infra diverging from your `.tf` config
- **Public / unencrypted S3 buckets**
- **Security groups open to `0.0.0.0/0`** on sensitive ports (22, 3389, 3306, 5432)
- **Unencrypted EBS volumes**
- **Missing required tags** (e.g. `owner`, `environment`, `cost-center`) — the
  #1 cause of "whose resource is this and can we delete it" tickets

## Pick your distribution channel

| Where you live | Install this | Channel |
|---|---|---|
| GitHub Actions CI | GitHub Action | [Marketplace listing](https://github.com/marketplace/actions/tf-drift-guard) |
| Standalone AWS account, scheduled scan | Terraform module | [Terraform Registry](https://registry.terraform.io/modules/SainiOps/drift-guard/aws) |
| EKS / Kubernetes cluster | Kyverno policies | [Artifact Hub](https://artifacthub.io/packages/search?repo=tf-drift-guard-kyverno-policies) |

---

### 1. GitHub Action (CI — recommended starting point)
```yaml
name: infra-guardrails
on: [pull_request]
jobs:
  drift-guard:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # if using OIDC to assume an AWS role
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::<account-id>:role/tf-drift-guard-readonly
          aws-region: us-east-1
      - uses: SainiOps/tf-drift-guard@v1.0.0
        with:
          aws-region: us-east-1
          required-tags: "owner,environment,cost-center"
          terraform-dir: "./infra"
          slack-webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
```
Fails the build (exit 1) if violations are found; posts a Slack alert if a
webhook URL is provided. IAM permissions needed: `ReadOnlyAccess` (or a
scoped-down equivalent) is sufficient — this tool never modifies your infra.

### 2. Terraform module (scheduled scan of a live AWS account)
```hcl
module "drift_guard" {
  source            = "SainiOps/drift-guard/aws"
  version           = "1.0.0"
  region            = "us-east-1"
  required_tags     = "owner,environment"
  slack_webhook_url = var.slack_webhook_url
  lambda_image_uri  = "<your-ecr-repo>:latest"
}
```
Deploys a scheduled Lambda (default `rate(6 hours)`) with the same checks,
so you get alerts even for infra changed outside of CI/Terraform.

### 3. Kyverno policies (enforce inside the cluster itself)
```bash
kubectl apply -f https://raw.githubusercontent.com/SainiOps/tf-drift-guard/main/kyverno-policies/require-labels/1.0.0/require-labels.yaml
kubectl apply -f https://raw.githubusercontent.com/SainiOps/tf-drift-guard/main/kyverno-policies/disallow-privileged/1.0.0/disallow-privileged.yaml
```
Requires [Kyverno](https://kyverno.io) installed in-cluster. Policies default
to `Audit` mode — flip to `Enforce` once teams have cleaned up violations.

## Pricing
- **Free forever**: GitHub Action, Terraform module, Kyverno policies (this repo).
- **Pro (coming soon)**: hosted multi-account dashboard, historical drift
  trends, SSO/RBAC, Slack + PagerDuty + Jira integrations. Sold as a SaaS
  Contract on AWS Marketplace — buy directly through your existing AWS
  committed spend, no procurement call needed.

## Repo layout
```
action.yml              # GitHub Action definition (Docker-based)
Dockerfile               # Container image for the action
scan.py                  # Core scan logic (boto3 + terraform CLI)
requirements.txt
terraform-module/        # source for the SainiOps/drift-guard/aws module
kyverno-policies/         # Artifact Hub "Kyverno policies" packages
helm-chart/               # (legacy) Helm packaging of the same policies
.github/workflows/        # CI to build/test/release this project itself
```

## Contributing / support
Issues and PRs welcome: https://github.com/SainiOps/tf-drift-guard/issues

## License
MIT — see [LICENSE](LICENSE).
