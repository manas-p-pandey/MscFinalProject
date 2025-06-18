import asyncio
import asyncpg

async def test_connection():
    try:
        conn = await asyncpg.connect("postgresql://postgres:Admin123@db:5432/mscds")
        print("✅ Connection successful!")
        await conn.close()
    except Exception as e:
        print("❌ Connection failed:", e)

asyncio.run(test_connection())
