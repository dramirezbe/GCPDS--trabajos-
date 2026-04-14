# 1

- 300k RBW
- 10MHz sample_rate
- FC 100M
- filter OFF

# 2 

- 10k RBW
- 15MHz sample_rate
- FC 100M
- filter OFF

# 3

- 1k RBW
- 20M sample_rate
- FC 100M
- filter OFF

# 4

- 1k RBW
- 20M sample_rate
- FC 2.4G
- filter ON

# LAN IP's

map LANs = sudo nmap -sn 192.168.0.0/24

ANE7 = 192.168.0.119
ANE8 = 192.168.0.118

# CMDs

use kitty with ssh = kitty +kitten ssh -p 21104 anepi@192.168.0.119

ANE7 = scp -P 21104 "anepi@192.168.0.119:~/telemetry/*.csv" ./ANE7-experiment/
ANE8 = scp -P 21104 "anepi@192.168.0.118:~/telemetry/*.csv" ./ANE8-experiment/
ANE9 = scp -J root@rsm.ane.gov.co:1222 -P 21104 "anepi@10.10.1.9:~/telemetry/*.csv" ./ANE9-experiment/.
ANE10 = scp -J root@rsm.ane.gov.co:1222 -P 21104 "anepi@10.10.1.10:~/telemetry/*.csv" ./ANE10-experiment/.  

password node:
AChuBRahuSp=R-0Ro

password-tunnel:
44"PJv43k}iS

### Force ppp0, mantain sshd eth0

sudo ip route del default dev eth0
sudo ip route add default dev ppp0


### Revert
sudo ip route del default dev ppp0
sudo ip route add default via <LOCAL_IP(ROUTER)> dev eth0


### Force HackRF MAX:

timeout 20m hackrf_transfer -r /dev/null -f 6000000000 -s 20000000 -a 1 -l 40 -g 62 -b 28000000


# STEPS EXPERIMENT

### IDLE_NO_PROCESSING

- NO PCB
- NO HACKRF
- NO PROCESSING

### HACKRF_PROCESSING

- NO PCB
- HACKRF PROCESSING MAX (timeout 5m hackrf_transfer -r /dev/null -f 6000000000 -s 20000000 -a 1 -l 40 -g 62 -b 28000000)

### LTE_PROCESSING

- PCB
- NO HACKRF
- LTE PROCESSING

### COMBINED

- PCB
- HACKRF PROCESSING MAX (timeout 5m hackrf_transfer -r /dev/null -f 6000000000 -s 20000000 -a 1 -l 40 -g 62 -b 28000000)
- LTE PROCESSING