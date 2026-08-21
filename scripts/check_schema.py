"""Prove that schema.sql can actually be applied to a database.

Why this exists.

`orchestrator/db.py:apply_schema` reads the whole file and hands it to a
single `cur.execute()`, which makes it one statement in one transaction. That
is a deliberate and reasonable choice -- it is atomic, so a half-applied schema
is impossible -- but it has a consequence that is easy to miss: ONE bad
statement anywhere in the file rolls back EVERY other statement, including all
the idempotent `ADD COLUMN IF NOT EXISTS` ones that were supposed to be safe.

And `IF NOT EXISTS` on a column guards the column, not the table. An
`ALTER TABLE t ADD COLUMN IF NOT EXISTS c` placed above the `CREATE TABLE t`
that defines `t` raises UndefinedTable, and takes the entire file down with it.

The orchestrator's lifespan handler then catches that, logs one line, and boots
anyway -- correct behaviour, because a database that is down at startup must not
stop the process from starting. So the failure mode is a process that runs
normally, answers `SELECT 1`, and returns 503 from every authenticated route
because the columns its queries name were never created. That shipped to
production once and survived for days.

Nothing in the suite catches it, because pytest in CI has no Postgres and
therefore never applies the schema to anything. This script is that missing
step: a real server, and the three orders a real deployment applies the file in.

Run it locally against the compose database before pushing a schema change:

    docker compose up -d db
    python scripts/check_schema.py \
        --dsn postgresql://marketplace:PASSWORD@localhost:5432/postgres \
        --schema orchestrator/schema.sql

The DSN must point at a database the script may create and drop scratch
databases beside; it never touches the one named in the DSN itself.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import psycopg


def _apply(dsn: str, database: str, path: Path) -> None:
    """Apply one schema file exactly the way apply_schema does.

    Same single execute, same single transaction. Using psql instead would
    quietly pass: psql runs statements one at a time and, without
    ON_ERROR_STOP, keeps going after a failure -- so it reports success on a
    file the application cannot apply. The whole defect being checked for lives
    in the difference between those two behaviours.
    """
    sql = path.read_text(encoding="utf-8")
    with psycopg.connect(_with_database(dsn, database)) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def _with_database(dsn: str, database: str) -> str:
    head, _, _ = dsn.rpartition("/")
    return f"{head}/{database}"


def _scratch(dsn: str) -> str:
    name = f"schemacheck_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{name}"')
    return name


def _drop(dsn: str, database: str) -> None:
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')


def _scenario(dsn: str, label: str, steps: list[Path]) -> bool:
    database = _scratch(dsn)
    try:
        for index, path in enumerate(steps, start=1):
            try:
                _apply(dsn, database, path)
            except psycopg.Error as exc:
                print(f"FAIL  {label}")
                print(f"      step {index} of {len(steps)} ({path}) raised:")
                print(f"      {exc.__class__.__name__}: {exc}")
                print(
                    "      Every statement in the file rolled back with it, "
                    "including the ADD COLUMNs."
                )
                return False
        print(f"ok    {label}")
        return True
    finally:
        _drop(dsn, database)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="Postgres DSN for a maintenance database")
    parser.add_argument("--schema", required=True, type=Path, help="the schema file under test")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="the currently-deployed schema, to check the upgrade path",
    )
    args = parser.parse_args()

    schema: Path = args.schema
    if not schema.is_file():
        print(f"no such schema file: {schema}")
        return 2

    # Three orders, because a deployment applies the file in all three and only
    # the first is ever exercised by a developer with a clean machine.
    scenarios: list[tuple[str, list[Path]]] = [
        ("fresh database", [schema]),
        ("applied twice (a redeploy against the same database)", [schema, schema]),
    ]
    if args.baseline is not None:
        if not args.baseline.is_file():
            print(f"no such baseline file: {args.baseline}")
            return 2
        scenarios.append(
            (
                "deployed onto the previous schema (what production does)",
                [args.baseline, schema, schema],
            )
        )
    else:
        print("note  no --baseline given; the upgrade path is unchecked")

    ok = True
    for label, steps in scenarios:
        if not _scenario(args.dsn, label, steps):
            ok = False

    if not ok:
        print()
        print("A statement in the file cannot run against a database in that state.")
        print("The usual cause is ordering: an ALTER TABLE above the CREATE TABLE it")
        print("alters. ADD COLUMN IF NOT EXISTS guards the column, not the table.")
        return 1

    print()
    print("schema.sql applies cleanly in every order a deployment uses.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
