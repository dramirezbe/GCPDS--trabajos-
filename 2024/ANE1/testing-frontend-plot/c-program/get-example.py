import cfg
log = cfg.set_logger()
from utils import RequestClient


client = RequestClient(cfg.API_URL, verbose=True, logger=log)


rc, resp = client.get(f"/{cfg.get_mac()}/configuration")
log.info(f"Response code: {rc}")
log.info(f"Response: {resp}")
print(resp.json())