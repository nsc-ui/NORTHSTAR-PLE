"""NORTHSTAR PLE: WebSocket protocol v1 server."""
import asyncio, json, os, logging
import websockets
from harness import solve

logging.basicConfig(level=os.getenv("LOG_LEVEL", "info"))
PORT = int(os.environ.get("PORT", "8000"))

async def session(ws):
    try:
        task = json.loads(await ws.recv())
        if task.get("type") != "task" or task.get("protocol") != 1:
            await ws.send(json.dumps({"type":"error","message":"Unsupported PLE protocol/task frame"}))
            return
        await solve(ws, task)
    except Exception as exc:
        logging.exception("task failed")
        try:
            await ws.send(json.dumps({"type":"error","message":f"NORTHSTAR failure: {type(exc).__name__}: {exc}"[:3000]}))
        except Exception:
            pass

async def main():
    async with websockets.serve(session, "0.0.0.0", PORT, max_size=16*2**20, ping_interval=None):
        logging.info("NORTHSTAR listening on %s", PORT)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
