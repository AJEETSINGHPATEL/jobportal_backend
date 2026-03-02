import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse, quote_plus, urlunparse
from dotenv import load_dotenv
from app.database.models import Base

load_dotenv()

# PostgreSQL Connection String
DATABASE_URL = os.getenv("DATABASE_URL")

def get_async_database_url(url: str) -> str:
    if not url:
        return ""
    
    # Clean up malformed strings (like DATABASE_URL="url" or just "url")
    # This is extremely aggressive to handle any combination of prefixes and quotes
    cleaned_url = url.strip()
    
    # Iteratively remove prefixes and quotes in case they are nested
    while any(cleaned_url.startswith(p) for p in ["DATABASE_URL=", '"', "'"]) or any(cleaned_url.endswith(p) for p in ['"', "'"]):
        if cleaned_url.startswith("DATABASE_URL="):
            cleaned_url = cleaned_url.replace("DATABASE_URL=", "", 1).strip()
        if cleaned_url.startswith('"') and cleaned_url.endswith('"'):
            cleaned_url = cleaned_url[1:-1].strip()
        elif cleaned_url.startswith("'") and cleaned_url.endswith("'"):
            cleaned_url = cleaned_url[1:-1].strip()
        else:
            # If it starts with a quote but doesn't end with one, or vice versa, break to avoid infinite loop
            break

    # Handle the case where the user might have literally included brackets [ ] around the password
    # e.g., postgresql://user:[pass]@host...
    # We should probably strip these if they exist as they are invalid in most URL schemes
    if ":// " not in cleaned_url and "://" in cleaned_url:
        scheme_part, rest = cleaned_url.split("://", 1)
        if "@" in rest:
            creds, host_part = rest.split("@", 1)
            if ":" in creds:
                user, password = creds.split(":", 1)
                # Strip literal brackets if present
                if password.startswith("[") and password.endswith("]"):
                    password = password[1:-1]
                # Re-encode to be safe
                password = quote_plus(password)
                cleaned_url = f"{scheme_part}://{user}:{password}@{host_part}"

    # Force asyncpg driver
    if cleaned_url.startswith("postgresql://"):
        cleaned_url = cleaned_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    return cleaned_url

DATABASE_URL = get_async_database_url(DATABASE_URL)

if not DATABASE_URL:
    print("CRITICAL: DATABASE_URL is not set!")
else:
    # Diagnostic masked logging
    masked = DATABASE_URL
    if "@" in DATABASE_URL:
        parts = DATABASE_URL.split("@")
        masked = "****@" + parts[1]
    print(f"DATABASE_URL prepared: {masked}")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    async with engine.begin() as conn:
        # For development, you might want to drop tables first
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)