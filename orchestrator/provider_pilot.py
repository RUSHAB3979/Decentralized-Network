"""Approve or pause one provider machine for the controlled inference pilot."""

from __future__ import annotations

import argparse
import getpass
import re
import sys
import warnings
from urllib.parse import urlsplit

import httpx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("approve", "pause"))
    parser.add_argument("node_id", help="machine ID from the provider console")
    parser.add_argument("--provider-account", required=True, help="expected provider account ID")
    parser.add_argument("--operator-email", required=True, help="email of the operator's customer account")
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="orchestrator base URL")
    args = parser.parse_args(argv)

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{7,63}", args.node_id):
        parser.error("invalid machine ID")
    if not re.fullmatch(r"prv_[a-f0-9]{32}", args.provider_account):
        parser.error("invalid provider account ID")
    try:
        url = urlsplit(args.url)
        local_http = url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}
        valid = (
            url.hostname and not (url.username or url.password or url.query or url.fragment)
            and (url.scheme == "https" or local_http)
        )
    except ValueError:
        valid = False
    if not valid:
        parser.error("use an HTTPS orchestrator URL or HTTP on loopback")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("Operator password: ")
    except (EOFError, getpass.GetPassWarning):
        print("Run this command from an interactive terminal to enter the password securely.", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130

    approved = args.action == "approve"
    try:
        with httpx.Client(base_url=args.url.rstrip("/"), timeout=60, follow_redirects=False) as client:
            login = client.post("/v1/auth/login", json={"email": args.operator_email, "password": password})
            login.raise_for_status()
            session = login.json()
            token = session.get("token") if isinstance(session, dict) else None
            if not isinstance(token, str) or not token:
                raise ValueError("missing operator session")
            headers = {"Authorization": f"Bearer {token}"}
            try:
                result = client.post(
                    f"/v1/operator/providers/nodes/{args.node_id}/inference-approval",
                    headers=headers,
                    json={"provider_account_id": args.provider_account, "approved": approved},
                )
                result.raise_for_status()
                state = result.json()
                if (
                    not isinstance(state, dict)
                    or state.get("node_id") != args.node_id
                    or state.get("provider_account_id") != args.provider_account
                    or state.get("inference_eligible") is not approved
                    or not isinstance(state.get("changed"), bool)
                ):
                    raise ValueError("unexpected approval result")
            finally:
                try:
                    client.post("/v1/auth/logout", headers=headers).raise_for_status()
                except httpx.HTTPError:
                    print("Could not confirm operator session logout.", file=sys.stderr)
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        message = detail if isinstance(detail, str) else "request refused"
        print(f"HTTP {exc.response.status_code}: {message}", file=sys.stderr)
        return 1
    except (httpx.RequestError, ValueError):
        print("Could not verify the orchestrator response. Check the console before retrying.", file=sys.stderr)
        return 1

    status = "approved" if state["inference_eligible"] else "paused"
    verb = "is now" if state["changed"] else "is already"
    print(f"{state['node_id']} {verb} {status} for inference.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
