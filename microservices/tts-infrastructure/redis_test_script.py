import asyncio
import arq
from arq.connections import RedisSettings

async def test():
    pool = await arq.create_pool(RedisSettings(host='localhost', port=6379))
    print("connected")
    await pool.close()

asyncio.run(test())