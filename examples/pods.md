# Kubernetes pods in five minutes

A pod is the smallest unit you deploy on Kubernetes. This short lesson explains what it contains and how to inspect one.

## What a pod contains

A pod wraps one or more containers that always run together on the same machine.

- Containers in a pod share one network address
- They can share storage volumes
- They start and stop together

## Why not one container per pod

Most pods do hold a single container. A second container belongs in the same pod only when it cannot work apart from the first, for example a helper that refreshes files the main application reads.

## Inspecting pods

You list the pods of a namespace, then describe one to see its events and the state of each container.

```
kubectl get pods
kubectl describe pod web
```
