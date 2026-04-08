#!/usr/bin/env bash
# Minimal wait-for-it: block until host:port is reachable.
set -euo pipefail

host="${1:?usage: wait-for-it.sh host:port -- cmd [args...]}"
shift || true
if [[ "${1:-}" == "--" ]]; then shift; fi

hostpart="${host%%:*}"
portpart="${host##*:}"

timeout="${TIMEOUT:-60}"
start=$SECONDS

until (exec 3<>"/dev/tcp/${hostpart}/${portpart}") 2>/dev/null; do
    if (( SECONDS - start >= timeout )); then
        echo "timeout waiting for ${host}" >&2
        exit 1
    fi
    sleep 1
done

exec "$@"
