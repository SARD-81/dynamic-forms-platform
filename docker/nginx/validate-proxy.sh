#!/bin/sh
set -eu
case "${NGINX_PROXY_SCHEME:-http}" in
  http) ;;
  https)
    case "${NGINX_INGRESS_BIND_ADDRESS:-}" in
      127.0.0.1|::1) ;;
      *) echo "Trusted TLS-edge mode requires loopback-only ingress" >&2; exit 1 ;;
    esac
    ;;
  *) echo "Invalid NGINX_PROXY_SCHEME: expected http or https" >&2; exit 1 ;;
esac
