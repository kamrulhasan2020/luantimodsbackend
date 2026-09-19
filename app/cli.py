"""Manage game servers and their API keys.

    python -m app.cli create-server NAME [--email EMAIL]
    python -m app.cli rotate-key NAME
    python -m app.cli revoke-key NAME
    python -m app.cli list-servers

A key is printed once when issued; only its hash is stored, so it can't be shown again.
"""

import argparse
import asyncio
import sys

from app.config import load_settings
from app.db import create_engine
from app.repositories.servers import ServerExistsError, ServerRepository
from app.security import generate_api_key, hash_api_key


async def run(args: argparse.Namespace) -> int:
    engine = create_engine(load_settings().database_url)
    servers = ServerRepository(engine)
    try:
        if args.command == "create-server":
            api_key = generate_api_key()
            try:
                await servers.create(args.name, args.email, hash_api_key(api_key))
            except ServerExistsError:
                print(f"error: server {args.name!r} already exists", file=sys.stderr)
                return 1
            print(f"Created server {args.name!r}. API key (shown once):\n{api_key}")

        elif args.command == "rotate-key":
            api_key = generate_api_key()
            if not await servers.set_api_key_hash(args.name, hash_api_key(api_key)):
                print(f"error: no such server {args.name!r}", file=sys.stderr)
                return 1
            print(f"New API key for {args.name!r} (shown once; the old key no longer works):")
            print(api_key)

        elif args.command == "revoke-key":
            if not await servers.set_api_key_hash(args.name, None):
                print(f"error: no such server {args.name!r}", file=sys.stderr)
                return 1
            print(f"Revoked API key for {args.name!r}.")

        elif args.command == "list-servers":
            for server in await servers.list_all():
                key = (
                    f"key since {server.api_key_created_at:%Y-%m-%d}"
                    if server.has_api_key
                    else "no key"
                )
                print(f"{server.name}\t{server.email or '-'}\t{key}")
    finally:
        await engine.dispose()
    return 0


def name_arg(value: str) -> str:
    value = value.strip()
    if not 1 <= len(value) <= 100:
        raise argparse.ArgumentTypeError("must be 1-100 characters")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-server", help="register a server and issue its first API key")
    create.add_argument("name", type=name_arg)
    create.add_argument("--email", help="owner's contact email (informational only)")
    for command, help_text in (
        ("rotate-key", "issue a new API key, invalidating the old one"),
        ("revoke-key", "invalidate the API key without issuing a new one"),
    ):
        sub.add_parser(command, help=help_text).add_argument("name", type=name_arg)
    sub.add_parser("list-servers", help="list registered servers")

    sys.exit(asyncio.run(run(parser.parse_args())))


if __name__ == "__main__":
    main()
