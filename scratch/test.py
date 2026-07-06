import asyncio
import sys
sys.path.append('c:/Users/GAMER/Downloads/Equisage-main/Equisage-main')
from dotenv import load_dotenv
load_dotenv()
from services.pipeline import run_pipeline
import time

async def test():
    print("Testing Pipeline on HDFCBANK...")
    r = await run_pipeline('HDFCBANK')
    if 'error' in r:
        print(f"ERROR: {r['error']}")
    else:
        print(f"Conviction: {r['synthesis']['conviction']}")
        print(f"Thesis: {r['synthesis']['one_line_thesis']}")
        print(f"Conflicts: {r['conflicts']}")
        print(f"LLM calls: {r['meta']['llm_calls']}")
        print(f"Total time: {r['meta']['total_seconds']}s")
        print(f"Red flags: {len(r['red_flags'])}")
        
    print("\nTesting Cache on TCS...")
    t1 = time.time()
    await run_pipeline('TCS')
    print(f"First call: {time.time()-t1:.1f}s")
    t2 = time.time()
    await run_pipeline('TCS')
    print(f"Cached call: {time.time()-t2:.3f}s")

if __name__ == '__main__':
    asyncio.run(test())
