"""
Seed demo museum + users for all roles (Postman-friendly).

Usage (from repo root, with DATABASE_URL and JWT_SECRET set):

    python -m app.db.seed

Credentials created/updated:

    SUPER_ADMIN   superadmin@tarik.test   Password123!
    MUSEUM_ADMIN  museumadmin@tarik.test  Password123!
    CURATOR       curator@tarik.test      Password123!
"""

from sqlalchemy import select

from app.core.enums import UserRole
from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.museum import Museum
from app.models.user import User

DEMO_PASSWORD = "Password123!"

DEMO_USERS = [
    {
        "email": "superadmin@tarik.com",
        "full_name": "Super Admin",
        "role": UserRole.SUPER_ADMIN,
        "assign_museum": False,
    },
    {
        "email": "museumadmin@tarik.com",
        "full_name": "Museum Admin",
        "role": UserRole.MUSEUM_ADMIN,
        "assign_museum": True,
    },
    {
        "email": "curator@tarik.com",
        "full_name": "Demo Curator",
        "role": UserRole.CURATOR,
        "assign_museum": True,
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        museum = db.scalar(
            select(Museum).where(Museum.name == "Tarik Demo Museum")
        )
        if museum is None:
            museum = Museum(
                name="Tarik Demo Museum",
                description="Seeded museum for Postman / local testing",
                city="Addis Ababa",
                country="Ethiopia",
            )
            db.add(museum)
            db.flush()
            print(f"Created museum: {museum.name} ({museum.id})")
        else:
            print(f"Museum already exists: {museum.name} ({museum.id})")

        password_hash = hash_password(DEMO_PASSWORD)

        for spec in DEMO_USERS:
            user = db.scalar(select(User).where(User.email == spec["email"]))
            museum_id = museum.id if spec["assign_museum"] else None

            if user is None:
                user = User(
                    email=spec["email"],
                    password_hash=password_hash,
                    full_name=spec["full_name"],
                    role=spec["role"],
                    museum_id=museum_id,
                )
                db.add(user)
                print(f"Created {spec['role'].value}: {spec['email']}")
            else:
                user.password_hash = password_hash
                user.full_name = spec["full_name"]
                user.role = spec["role"]
                user.museum_id = museum_id
                print(f"Updated {spec['role'].value}: {spec['email']}")

        db.commit()
        print()
        print("Seed complete. Login with any of:")
        for spec in DEMO_USERS:
            print(f"  {spec['email']} / {DEMO_PASSWORD}")
        print(f"Demo museum_id: {museum.id}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
