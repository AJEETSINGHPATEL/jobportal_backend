import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import create_tables

async def main():
    print("Connecting to Supabase and creating tables...")
    try:
        await create_tables()
        print("Tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    asyncio.run(main())
