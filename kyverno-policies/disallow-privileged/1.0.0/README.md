# Disallow Privileged Containers

Kyverno ClusterPolicy that blocks Pods requesting `privileged: true` in
their security context.

## Install
```bash
kubectl apply -f disallow-privileged.yaml
```
