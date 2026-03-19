cd /root/extern-repos/GCPDS-trabajos/ANE2/Plat-Waterfall-Fix/
git fetch
git reset --hard origin/main
git pull

rm -rf /opt/ane-realtime/frontend/src/*
cp -r frontend/src/* /opt/ane-realtime/frontend/src/

cd /opt/ane-realtime
VITE_API_URL=/api VITE_WS_URL=/ws docker compose build frontend
docker compose up -d frontend