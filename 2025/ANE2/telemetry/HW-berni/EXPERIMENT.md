# Stress Test Platform

### 1

- 300k RBW
- 10MHz sample_rate
- FC 100M
- filter OFF

### 2 

- 10k RBW
- 15MHz sample_rate
- FC 100M
- filter OFF

### 3

- 1k RBW
- 20M sample_rate
- FC 100M
- filter OFF

### 4

- 1k RBW
- 20M sample_rate
- FC 2.4G
- filter ON


# STEPS EXPERIMENT folders

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