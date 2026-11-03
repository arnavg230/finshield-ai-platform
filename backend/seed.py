"""
Create the demo accounts and a few sample transactions.

Run once after the database is created:
    python seed.py
"""
from app.database import Base, SessionLocal, engine
from app.models import (
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_COMPLIANCE,
    ROLE_CUSTOMER,
    User,
)
from app.security import hash_password

DEMO_USERS = [
    ("admin", "admin@thapar.edu", "Admin@123", "System Administrator", ROLE_ADMIN),
    ("analyst", "analyst@thapar.edu", "Analyst@123", "Fraud Analyst", ROLE_ANALYST),
    ("officer", "officer@thapar.edu", "Officer@123", "Compliance Officer", ROLE_COMPLIANCE),
    ("customer", "customer@thapar.edu", "Customer@123", "Demo Customer", ROLE_CUSTOMER),
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        created = 0
        for username, email, password, full_name, role in DEMO_USERS:
            if db.query(User).filter(User.username == username).first():
                print(f"  {username:10s} already exists")
                continue
            db.add(
                User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    hashed_password=hash_password(password),
                    role=role,
                )
            )
            created += 1
            print(f"  {username:10s} created  (role: {role}, password: {password})")
        db.commit()
        print(f"\nDone. {created} new user(s) created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
