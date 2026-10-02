import argparse
import math
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage()
        self.exit(2, "Invalid arguments. Use --help for accepted options.\n")


def request_status(url, timeout):
    opener = build_opener(NoRedirect())
    request = Request(
        url,
        headers={"User-Agent": "production-smoke-verifier"},
    )

    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status
    except HTTPError as error:
        status = error.code
        error.close()
        return status


def check_route(name, url, expected_status, timeout, requester=None):
    if requester is None:
        requester = request_status

    try:
        status = requester(url, timeout)
    except TimeoutError:
        print(f"FAIL {name}: timeout")
        return False
    except URLError as error:
        if isinstance(error.reason, TimeoutError):
            print(f"FAIL {name}: timeout")
        else:
            print(f"FAIL {name}: connection error")
        return False
    except OSError:
        print(f"FAIL {name}: connection error")
        return False

    if status != expected_status:
        print(f"FAIL {name}: HTTP {status}, expected {expected_status}")
        return False

    print(f"PASS {name}: HTTP {status}")
    return True


def positive_timeout(value):
    try:
        timeout = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Timeout must be a positive number.") from None

    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("Timeout must be a positive finite number.")

    return timeout


def base_url(value):
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid base URL.") from None

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or port == 0
    ):
        raise argparse.ArgumentTypeError(
            "Base URL must be an HTTP(S) origin without credentials, path, query or fragment."
        )

    return value.rstrip("/")


def route_path(value):
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid route path.") from None

    if (
        not value.startswith("/")
        or value.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or parsed.fragment
        or "\\" in value
        or any(character.isspace() for character in value)
    ):
        raise argparse.ArgumentTypeError(
            "Route must be a path starting with /, without a host or fragment."
        )

    return value


def http_status(value):
    try:
        status = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Status must be an integer from 100 to 599.") from None

    if not 100 <= status <= 599:
        raise argparse.ArgumentTypeError("Status must be an integer from 100 to 599.")

    return status


def main(argv=None):
    parser = SafeArgumentParser(description="Verify the public production HTTP boundary.")
    parser.add_argument("--base-url", required=True, type=base_url)
    parser.add_argument("--timeout", type=positive_timeout, default=5.0)

    parser.add_argument("--login-path", type=route_path, default="/accounts/login/")
    parser.add_argument("--api-path", type=route_path, default="/api/v1/")
    parser.add_argument(
        "--schema-path",
        type=route_path,
        default="/api/schema/?format=json",
    )

    parser.add_argument("--liveness-path", type=route_path)
    parser.add_argument("--readiness-path", type=route_path)
    parser.add_argument("--static-path", type=route_path)
    parser.add_argument("--require-all", action="store_true")

    for name in ("login", "api", "schema", "liveness", "readiness", "static"):
        parser.add_argument(
            f"--{name}-status",
            type=http_status,
            default=200,
        )

    args = parser.parse_args(argv)

    optional_checks = (
        ("liveness", args.liveness_path),
        ("readiness", args.readiness_path),
        ("static", args.static_path),
    )

    if args.require_all and any(path is None for _, path in optional_checks):
        parser.error("--require-all needs liveness, readiness and static paths.")

    checks = [
        ("login", args.login_path),
        ("api", args.api_path),
        ("schema", args.schema_path),
    ]

    for name, path in optional_checks:
        if path is not None:
            checks.append((name, path))

    failed = False

    for name, path in checks:
        passed = check_route(
            name,
            args.base_url + path,
            expected_status=getattr(args, f"{name}_status"),
            timeout=args.timeout,
        )
        if not passed:
            failed = True

    for name, path in optional_checks:
        if path is None:
            print(f"SKIP {name}: path not configured")

    if failed:
        print("HTTP verification failed.")
        return 1

    if all(path is not None for _, path in optional_checks):
        print("All configured HTTP/static checks passed.")
    else:
        print("Partial HTTP verification passed; health/static coverage is incomplete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
