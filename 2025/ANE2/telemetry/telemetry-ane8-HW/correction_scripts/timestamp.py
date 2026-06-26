import csv, glob, os
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

target_unix = 1775753304653
tz = timezone(timedelta(hours=-5)) # Colombia UTC-5

for file in glob.glob('**/*_idle.csv', recursive=True):
    with open(file, 'r') as f:
        rows = list(csv.reader(f))
    
    offset = target_unix - int(rows[1][1])
    
    for row in rows[1:]:
        new_unix = int(row[1]) + offset
        row[1] = str(new_unix)
        row[0] = datetime.fromtimestamp(new_unix / 1000.0, tz).strftime('%H:%M:%S.%f')[:-3]
        
    new_file = os.path.join(os.path.dirname(file), '20260409_114824_idle.csv')
    
    with open(new_file, 'w', newline='') as f:
        csv.writer(f).writerows(rows)
        
    os.remove(file)