# Require Owner & Environment Labels

Kyverno ClusterPolicy that enforces `owner` and `environment` labels on
Deployments, StatefulSets and DaemonSets — matching the same tagging
guardrail enforced on AWS resources by [TF Drift Guard](https://github.com/SainiOps/tf-drift-guard).

## Install
```bash
kubectl apply -f require-labels.yaml
```
