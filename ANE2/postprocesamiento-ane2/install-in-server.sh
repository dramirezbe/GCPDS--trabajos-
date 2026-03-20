cd /root/extern-repos/GCPDS-trabajos/ANE2/postprocesamiento-ane2/
git fetch
git reset --hard origin/main
git pull

# Sincroniza archivos del repo a /opt:
# - Sobrescribe los que existan en destino
# - Copia nuevos archivos
# - NO borra archivos locales extra en /opt (sin --delete)
rsync -av --exclude '.git/' ./ /opt/ane-realtime/postprocesamiento/

cd /opt/ane-realtime
docker compose build postprocesamiento
docker compose up -d postprocesamiento
