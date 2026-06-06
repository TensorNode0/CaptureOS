import os
from motor.motor_asyncio import AsyncIOMotorClient

_client = AsyncIOMotorClient(os.environ["MONGO_URL"], tz_aware=True)
db = _client[os.environ["DB_NAME"]]


async def ensure_indexes():
    await db.users.create_index("email", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.email_verify_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")
    await db.memberships.create_index([("organizationId", 1), ("userId", 1)])
    await db.memberships.create_index("invitedEmail")
    await db.opportunities.create_index([("organizationId", 1)])
    await db.opportunities.create_index([("organizationId", 1), ("solNumber", 1)])
    await db.auditLog.create_index([("organizationId", 1), ("at", -1)])
