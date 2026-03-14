import asyncio
from vision_agent import get_vision_agent

async def main():
    agent = get_vision_agent()
    print("Testing vision agent...")
    res = await agent.batch_analyze(["AAPL", "MSFT"], "1M", ["SMA 20"])
    for r in res:
        print(f"Symbol: {r[0]}")
        print(f"Analysis keys: {r[1].keys()}")
        print(f"Image Path: {r[2]}")
        
if __name__ == "__main__":
    asyncio.run(main())
