"""
MongoDB-backed user store for authentication.

Local dev: point MONGODB_URI at a local `mongod` (default
mongodb://localhost:27017) — no auth, no setup beyond having MongoDB
installed and running.

Production: point MONGODB_URI at a MongoDB Atlas connection string (free
tier is enough for this project). See the README's Deployment section.

Passwords are hashed with bcrypt directly (not via `passlib`, which has a
long-standing, unresolved compatibility bug with modern bcrypt releases).
"""
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend import config

# Module-level client/collection so the connection is established once per
# process and reused across requests. Exposed as module attributes (rather
# than hidden in a closure) so tests can swap in a mongomock collection
# without needing a real MongoDB server.
#
# serverSelectionTimeoutMS keeps a misconfigured/unreachable MONGODB_URI from
# hanging the whole app — operations fail fast with a clear PyMongoError
# instead of hanging indefinitely.
_client = MongoClient(config.MONGODB_URI, serverSelectionTimeoutMS=5000)
_db = _client[config.MONGODB_DB_NAME]
users_collection = _db["users"]

try:
    # Enforce email uniqueness at the database level (in addition to the
    # application-level check in create_user), so a race between two
    # concurrent signups with the same email can't create two accounts.
    users_collection.create_index("email", unique=True)
except PyMongoError as e:
    print(
        f"WARNING: Could not reach MongoDB at startup ({e}). "
        f"Check MONGODB_URI in .env — is MongoDB running locally, or is your "
        f"Atlas connection string correct? Auth endpoints will fail until "
        f"this is resolved."
    )


def hash_password(password: str) -> str:
    # bcrypt only uses the first 72 bytes of the input; encode explicitly so
    # this is measured in bytes, not characters (matters for non-ASCII input).
    password_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except ValueError:
        # Malformed/unrecognized hash format.
        return False


def _to_public_dict(doc: dict) -> dict:
    """Strip Mongo/internal fields, keep the shape the rest of the app expects."""
    return {
        "id": doc["_id"],
        "email": doc["email"],
        "name": doc["name"],
        "created_at": doc["created_at"],
    }


def create_user(email: str, name: str, password: str) -> dict:
    email = email.strip().lower()
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    created_at = datetime.now(timezone.utc).isoformat()

    doc = {
        "_id": user_id,
        "email": email,
        "name": name,
        "password_hash": password_hash,
        "created_at": created_at,
    }

    try:
        users_collection.insert_one(doc)
    except DuplicateKeyError:
        raise ValueError("An account with this email already exists.")

    return _to_public_dict(doc)


def get_user_by_email(email: str) -> dict | None:
    email = email.strip().lower()
    doc = users_collection.find_one({"email": email})
    if not doc:
        return None
    return {
        "id": doc["_id"],
        "email": doc["email"],
        "name": doc["name"],
        "password_hash": doc["password_hash"],
        "created_at": doc["created_at"],
    }


def get_user_by_id(user_id: str) -> dict | None:
    doc = users_collection.find_one({"_id": user_id})
    if not doc:
        return None
    return _to_public_dict(doc)
