import cfg
log = cfg.set_logger()
from utils import ZmqPub, ZmqSub, RequestClient
import asyncio

topic_data = "data"

async def run_server():
    log.info("Starting server...")
    pub = ZmqPub(addr=cfg.IPC_CMD_ADDR)
    sub = ZmqSub(addr=cfg.IPC_DATA_ADDR, topic=topic_data)

    client = RequestClient(base_url=cfg.API_URL, api_key=cfg.API_KEY)

    # Allow ZMQ connections to settle
    await asyncio.sleep(0.5)