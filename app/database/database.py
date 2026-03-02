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
    
    # Force asyncpg driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not url.startswith("postgresql+asyncpg://"):
        # If it's just a raw connection string without prefix, prepending might be risky, 
        # but the user provided a postgresql:// one.
        pass

    try:
        # Parse the URL to handle special characters in password
        parsed = urlparse(url)
        if parsed.password:
            # Re-encode the password part only
            # The password might contain special characters like '?' or '@'
            encoded_password = quote_plus(parsed.password)
            
            # Reconstruct the netloc (user:pass@host:port)
            user_part = parsed.username or ""
            password_part = f":{encoded_password}"
            host_part = parsed.hostname or ""
            port_part = f":{parsed.port}" if parsed.port else ""
            
            new_netloc = f"{user_part}{password_part}@{host_part}{port_part}"
            
            # Reconstruct the full URL
            url = urlunparse((
                parsed.scheme,
                new_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
    except Exception as e:
        print(f"Warning: Could not perfectly parse/re-encode DATABASE_URL: {e}")
    
    return url

DATABASE_URL = get_async_database_url(DATABASE_URL)

if not DATABASE_URL:
    print("CRITICAL: DATABASE_URL is not set!")

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