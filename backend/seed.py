"""Seed an initial admin user. Usage:

    python seed.py --email admin@example.com --password secret --role admin
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.api.auth import hash_password
from app.config import load_settings
from app.db.models import User
from app.db.schema import apply_schema
from app.db.session import init_engine, session_scope


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", default="admin", choices=["admin", "viewer"])
    args = parser.parse_args(argv)

    settings = load_settings()
    init_engine(settings.database_url)
    apply_schema(settings.database_url)

    with session_scope() as db:
        existing = db.execute(select(User).where(User.email == args.email)).scalar_one_or_none()
        if existing:
            print(f"User {args.email} already exists; updating password/role.")
            existing.password_hash = hash_password(args.password)
            existing.role = args.role
        else:
            db.add(User(email=args.email, password_hash=hash_password(args.password),
                        role=args.role))
            print(f"Created user {args.email} ({args.role}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
