"""Create accounts by hand, for a deployment whose signup door is shut.

    python -m orchestrator.seed_users alice@example.com bob@example.com
    python -m orchestrator.seed_users --provider provider@example.com

Prints one email/password pair per account and then forgets them. There is no
way to ask for them again, because nothing here stores a password anywhere: the
database gets a scrypt digest, and the plaintext exists only in the terminal
this was run in.

That is the point, and it is worth stating why rather than treating it as an
inconvenience. The obvious alternative -- write the pairs to a file so they can
be looked up later -- creates a file whose entire content is working
credentials, sitting in a repository directory, one `git add -A` away from
being permanent. This repository has already done that once: a password is
still readable in its history at commit a276efe. A tool that makes the same
mistake easy will eventually be used to make it.

So: copy the output into whatever private channel the team uses, close the
terminal, and re-run with --reset if somebody loses theirs.

Passwords are 22 characters from `secrets.token_urlsafe`, roughly 128 bits.
They are not memorable and are not meant to be -- these go in a password
manager. Anything a person can retype from memory is also something a person
can guess, and seeding six guessable accounts behind a closed signup form would
leave this deployment worse off than leaving signup open.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from uuid import uuid4

import psycopg
from psycopg import sql

from orchestrator import auth, db

# 16 bytes -> 22 URL-safe characters, comfortably past the 10-character floor
# that SignupRequest enforces on the public endpoint. This script writes
# straight to the table and so bypasses that model; matching its rules anyway
# keeps seeded accounts indistinguishable from real ones.
PASSWORD_BYTES = 16


def generate_password() -> str:
    return secrets.token_urlsafe(PASSWORD_BYTES)


def seed(email: str, *, reset: bool, provider: bool = False) -> tuple[str, str] | None:
    """Create or rotate one account. Returns (email, password), or None.

    None means the address already had an account and --reset was not given.
    That is the safe default: silently rotating the password of an account
    somebody is already using would lock them out at the moment this script is
    re-run to add one more colleague, and nothing would report it.
    """
    normalised = auth.normalise_email(email)
    password = generate_password()
    password_hash = auth.hash_password(password)
    table = sql.Identifier("provider_accounts" if provider else "users")
    id_column = sql.Identifier("provider_account_id" if provider else "user_id")
    id_prefix = "prv" if provider else "usr"

    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("""
                INSERT INTO {table} ({id_column}, email, password_hash, display_name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING {id_column}
                """).format(table=table, id_column=id_column),
                (
                    f"{id_prefix}_{uuid4().hex}",
                    normalised,
                    password_hash,
                    normalised.split("@", 1)[0],
                ),
            )
            created = cur.fetchone() is not None

            if not created and reset:
                cur.execute(
                    sql.SQL("UPDATE {} SET password_hash = %s WHERE email = %s").format(table),
                    (password_hash, normalised),
                )
                # Every existing session keeps working after a password change,
                # because sessions are their own rows and nothing here touches
                # them. That is deliberate for a rotation somebody asked for.
                # It would be wrong for a compromised account, which needs the
                # sessions revoked too -- and that is not what this script is
                # for. Do it in SQL and say so out loud.
        conn.commit()

    if not created and not reset:
        return None
    return normalised, password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m orchestrator.seed_users",
        description="Create accounts directly, bypassing the signup endpoint.",
    )
    parser.add_argument("emails", nargs="+", help="one or more email addresses")
    parser.add_argument(
        "--provider",
        action="store_true",
        help="seed accounts in the provider console realm",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="rotate the password if the address already has an account",
    )
    args = parser.parse_args(argv)

    try:
        results = [
            (email, seed(email, reset=args.reset, provider=args.provider)) for email in args.emails
        ]
    except db.NotConfigured as exc:
        # Distinct from a connection failure, and the distinction matters:
        # this one is fixed by setting a variable, not by starting Postgres.
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (psycopg.Error, OSError) as exc:
        print(f"error: database unreachable: {exc}", file=sys.stderr)
        return 1

    created = [pair for _, pair in results if pair is not None]
    skipped = [email for email, pair in results if pair is None]

    if created:
        print()
        print("  Copy these now. They are not stored and cannot be shown again.")
        print()
        width = max(len(email) for email, _ in created)
        for email, password in created:
            print(f"  {email.ljust(width)}   {password}")
        print()

    for email in skipped:
        print(f"  skipped {email}: already has an account (use --reset to rotate)")

    if skipped and not created:
        print()
        print("  Nothing created.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
