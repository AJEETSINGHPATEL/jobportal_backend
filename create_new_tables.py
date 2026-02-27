import asyncio
from app.database.database import create_tables

async def main():
    print("Creating tables...")
    await create_tables()
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
