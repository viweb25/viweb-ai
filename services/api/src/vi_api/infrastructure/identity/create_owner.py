"""Provision an owner from a trusted administrator's terminal."""

import argparse
import asyncio
import re
from getpass import getpass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from vi_api.infrastructure.database.session import Session, engine
from vi_api.infrastructure.identity.passwords import hash_password


async def create_owner(email: str, organisation: str | UUID, password_hash: str) -> None:
    try:
        async with Session.begin() as session:
            if isinstance(organisation, UUID):
                org_id = await session.scalar(
                    text("SELECT id FROM public.organisations WHERE id = :id"), {"id": organisation}
                )
                if org_id is None:
                    raise SystemExit("Organisation not found.")
            else:
                org_id = await session.scalar(
                    text("""
                        INSERT INTO public.organisations (id, name)
                        VALUES (gen_random_uuid(), :name)
                        RETURNING id
                    """),
                    {"name": organisation},
                )
            user_id = await session.scalar(
                text("INSERT INTO identity.users (email) VALUES (:email) RETURNING id"),
                {"email": email},
            )
            await session.execute(
                text("""
                    INSERT INTO identity.password_credentials (user_id, email, password_hash)
                    VALUES (:user_id, :email, :password_hash)
                """),
                {"user_id": user_id, "email": email, "password_hash": password_hash},
            )
            await session.execute(
                text("""
                    INSERT INTO identity.memberships (org_id, user_id, role)
                    VALUES (:org_id, :user_id, 'owner')
                """),
                {"org_id": org_id, "user_id": user_id},
            )
    except IntegrityError:
        raise SystemExit(
            "Owner could not be created. An account may already use that email."
        ) from None
    finally:
        await engine.dispose()
    print(f"Owner created. User ID: {user_id}. Organisation ID: {org_id}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    company = parser.add_mutually_exclusive_group(required=True)
    company.add_argument("--organisation")
    company.add_argument("--org-id", type=UUID)
    args = parser.parse_args()
    email = args.email.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+", email):
        parser.error("Enter a valid email address.")
    if args.organisation is not None and not 1 <= len(args.organisation.strip()) <= 200:
        parser.error("Organisation names must contain 1 to 200 characters.")
    password = getpass("New password (at least 15 characters): ")
    if not 15 <= len(password) <= 128:
        parser.error("Use 15 to 128 characters.")
    if password != getpass("Confirm password: "):
        parser.error("Passwords do not match.")
    asyncio.run(
        create_owner(email, args.org_id or args.organisation.strip(), hash_password(password))
    )


if __name__ == "__main__":
    main()
