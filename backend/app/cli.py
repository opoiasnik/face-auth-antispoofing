"""Administrative command line.

Usage::

    python -m app.cli generate-secrets
    python -m app.cli promote <username>
"""

from __future__ import annotations

import argparse
import secrets
import sys

from cryptography.fernet import Fernet


def _generate_secrets() -> int:
    print(f"FA_SECURITY__JWT_SECRET={secrets.token_urlsafe(48)}")
    print(f"FA_SECURITY__TEMPLATE_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
    return 0


def _promote(username: str, revoke: bool) -> int:
    from app.core.config import get_settings
    from app.db.session import create_db_engine, create_session_factory
    from app.repositories.users import UserRepository

    settings = get_settings()
    factory = create_session_factory(create_db_engine(settings.database_url))
    with factory() as session, session.begin():
        user = UserRepository(session).get_by_username(username.lower())
        if user is None:
            print(f"User '{username}' not found", file=sys.stderr)
            return 1
        user.is_admin = not revoke
    print(f"User '{username}' admin={not revoke}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate-secrets", help="Print fresh secrets for the .env file")
    promote = sub.add_parser("promote", help="Grant (or revoke) the administrator role")
    promote.add_argument("username")
    promote.add_argument("--revoke", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "generate-secrets":
        return _generate_secrets()
    return _promote(args.username, args.revoke)


if __name__ == "__main__":
    raise SystemExit(main())
