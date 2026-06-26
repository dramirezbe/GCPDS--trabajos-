"""@file scheduler.py
@brief Main backend brain, uses crontab to schedule jobs, uses httpx and asyncio to make GET requests to /jobs API, the pograms will execute each 5minutes (No superloop), or after an Spectrum Acquisition.
"""
from crontab import CronTab

cron = CronTab(user="root")