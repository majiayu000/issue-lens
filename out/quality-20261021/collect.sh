#!/bin/sh
# 状态机/分布式类仓库:只取带 bug 标签的已完成 issue,按评论数取前 400 条。
cd "$(dirname "$0")/../.."
while IFS='|' read repo label; do
  extra=""; [ "$repo" = "etcd-io/etcd" ] && extra="--refresh"
  for try in 1 2 3; do
    python3 s02_fetch_issues.py --forms distributed --repos "$repo" --label "$label" \
      --sort comments --max-issues 400 $extra && break
    echo "RETRY $repo ($try)"; sleep 20
  done
done <<'LIST'
etcd-io/etcd|type/bug
hashicorp/consul|type/bug
hashicorp/nomad|type/bug
cockroachdb/cockroach|C-bug
tikv/tikv|type/bug
pingcap/tidb|type/bug
facebook/rocksdb|bug
vitessio/vitess|Type: Bug
yugabyte/yugabyte-db|kind/bug
scylladb/scylladb|bug
kubernetes/kubernetes|kind/bug
containerd/containerd|kind/bug
moby/moby|kind/bug
nats-io/nats-server|defect
temporalio/temporal|bug
hashicorp/raft|bug
databendlabs/openraft|C-bug
LIST
