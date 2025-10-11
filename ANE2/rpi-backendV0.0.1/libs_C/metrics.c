/**
 * @file metrics.c
 * @brief This file contains functions to get system metrics such as CPU usage, memory usage, disk usage, and network usage.
 */

// Compile with: gcc -fPIC -shared -o metrics.so metrics.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/statvfs.h>
#include <unistd.h>
#include <ctype.h>
#include <dirent.h>

typedef struct {
    long long user;
    long long nice;
    long long system;
    long long idle;
    long long iowait;
    long long irq;
    long long softirq;
    long long steal;
    long long guest;
    long long guest_nice;
} CPUTimes;

static int get_cpu_core_count() {
    return (int)sysconf(_SC_NPROCESSORS_ONLN);
}

static int read_cpu_line_for_core(char *buf, size_t bufsz, int core_index) {
    FILE *fp = fopen("/proc/stat", "r");
    if (!fp) return 0;

    while (fgets(buf, (int)bufsz, fp)) {
        if (core_index == -1) {
            if (strncmp(buf, "cpu ", 4) == 0) { // overall
                fclose(fp);
                return 1;
            }
        } else {
            if (strncmp(buf, "cpu", 3) == 0 && isdigit((unsigned char)buf[3])) {
                int idx;
                if (sscanf(buf, "cpu%d", &idx) == 1 && idx == core_index) {
                    fclose(fp);
                    return 1;
                }
            }
        }
    }
    fclose(fp);
    return 0;
}

static void parse_cpu_times_line(const char *line, CPUTimes *ct) {
    memset(ct, 0, sizeof(*ct));
    sscanf(line, "%*s %lld %lld %lld %lld %lld %lld %lld %lld %lld %lld",
           &ct->user, &ct->nice, &ct->system, &ct->idle, &ct->iowait,
           &ct->irq, &ct->softirq, &ct->steal, &ct->guest, &ct->guest_nice);
}

static void get_cpu_times(CPUTimes *out, int core_index) {
    char line[512];
    if (!read_cpu_line_for_core(line, sizeof(line), core_index)) {
        memset(out, 0, sizeof(*out));
        return;
    }
    parse_cpu_times_line(line, out);
}

static double calculate_cpu_usage(const CPUTimes *prev, const CPUTimes *curr) {
    long long prev_idle = prev->idle + prev->iowait;
    long long idle = curr->idle + curr->iowait;

    long long prev_non_idle = prev->user + prev->nice + prev->system + prev->irq + prev->softirq + prev->steal;
    long long non_idle = curr->user + curr->nice + curr->system + curr->irq + curr->softirq + curr->steal;

    long long prev_total = prev_idle + prev_non_idle;
    long long total = idle + non_idle;

    long long totald = total - prev_total;
    long long idled = idle - prev_idle;

    if (totald <= 0) return 0.0;
    double cpu_percentage = (double)(totald - idled) * 100.0 / (double)totald;
    if (cpu_percentage < 0.0) cpu_percentage = 0.0;
    return cpu_percentage;
}

static void get_memory_info(long *ram_total_kb, long *ram_used_kb, long *swap_total_kb, long *swap_used_kb) {
    *ram_total_kb = *ram_used_kb = *swap_total_kb = *swap_used_kb = 0;
    FILE *fp = fopen("/proc/meminfo", "r");
    if (!fp) return;
    char line[256];
    long mem_total = 0, mem_free = 0, buffers = 0, cached = 0, sreclaimable = 0;
    long swap_total = 0, swap_free = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "MemTotal:", 9) == 0) sscanf(line+9, "%ld", &mem_total);
        else if (strncmp(line, "MemFree:", 8) == 0) sscanf(line+8, "%ld", &mem_free);
        else if (strncmp(line, "Buffers:", 8) == 0) sscanf(line+8, "%ld", &buffers);
        else if (strncmp(line, "Cached:", 7) == 0) sscanf(line+7, "%ld", &cached);
        else if (strncmp(line, "SReclaimable:", 13) == 0) sscanf(line+13, "%ld", &sreclaimable);
        else if (strncmp(line, "SwapTotal:", 10) == 0) sscanf(line+10, "%ld", &swap_total);
        else if (strncmp(line, "SwapFree:", 9) == 0) sscanf(line+9, "%ld", &swap_free);
    }
    fclose(fp);

    *ram_total_kb = mem_total;
    *ram_used_kb = mem_total - mem_free - buffers - cached - sreclaimable;
    if (*ram_used_kb < 0) *ram_used_kb = 0;

    *swap_total_kb = swap_total;
    *swap_used_kb = swap_total - swap_free;
    if (*swap_used_kb < 0) *swap_used_kb = 0;
}

static void get_disk_usage(double *disk_total_gb, double *disk_used_gb) {
    struct statvfs s;
    *disk_total_gb = *disk_used_gb = 0.0;
    if (statvfs("/", &s) != 0) return;
    unsigned long long total_bytes = (unsigned long long)s.f_blocks * (unsigned long long)s.f_frsize;
    unsigned long long used_bytes = (unsigned long long)(s.f_blocks - s.f_bfree) * (unsigned long long)s.f_frsize;
    *disk_total_gb = (double)total_bytes / (1024.0 * 1024.0 * 1024.0);
    *disk_used_gb  = (double)used_bytes  / (1024.0 * 1024.0 * 1024.0);
}

static void get_mac_address(char *mac_address, size_t size) {
    if (!mac_address || size == 0) return;

    DIR *d = opendir("/sys/class/net");
    if (!d) {
        strncpy(mac_address, "N/A", size - 1);
        mac_address[size - 1] = '\0';
        return;
    }

    struct dirent *ent;
    char path[300]; // a bit larger than 256
    int found = 0;

    while ((ent = readdir(d)) != NULL) {
        if (ent->d_name[0] == '.') continue; // skip . and ..
        // Skip loopback
        if (strcmp(ent->d_name, "lo") == 0) continue;

        // Use snprintf safely — limit name length explicitly
        snprintf(path, sizeof(path) - 1, "/sys/class/net/%.100s/address", ent->d_name);
        path[sizeof(path) - 1] = '\0';

        FILE *fp = fopen(path, "r");
        if (fp) {
            if (fgets(mac_address, (int)size, fp)) {
                // remove trailing newline if present
                mac_address[strcspn(mac_address, "\n")] = '\0';
                found = 1;
                fclose(fp);
                break;
            }
            fclose(fp);
        }
    }
    closedir(d);

    if (!found) {
        strncpy(mac_address, "N/A", size - 1);
        mac_address[size - 1] = '\0';
    }
}

/* Read CPU temperature in Celsius.
 * Tries common sysfs thermal path: /sys/class/thermal/thermal_zone0/temp
 * Returns temperature in degrees C (e.g. 50.23). On failure returns 0.0.
 */
static double get_cpu_temp_c(void) {
    const char *paths[] = {
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/thermal/thermal_zone1/temp",
        "/sys/devices/virtual/thermal/thermal_zone0/temp"
    };
    for (size_t i = 0; i < sizeof(paths)/sizeof(paths[0]); ++i) {
        FILE *fp = fopen(paths[i], "r");
        if (!fp) continue;
        long long raw = 0;
        if (fscanf(fp, "%lld", &raw) == 1) {
            fclose(fp);
            // Common units: millidegrees (e.g. 50000) or degrees (e.g. 50)
            if (raw > 1000) return (double)raw / 1000.0;
            return (double)raw;
        }
        fclose(fp);
    }
    // fallback (no thermal sensor found)
    return 0.0;
}

/* Public API: returns a malloc'd string; caller must free with free_system_info_string */
char* get_system_info() {
    int cores = get_cpu_core_count();
    if (cores <= 0) cores = 1;

    CPUTimes *prev_cores = (CPUTimes*)malloc(sizeof(CPUTimes) * cores);
    CPUTimes *curr_cores = (CPUTimes*)malloc(sizeof(CPUTimes) * cores);
    CPUTimes prev_overall, curr_overall;

    if (!prev_cores || !curr_cores) {
        free(prev_cores);
        free(curr_cores);
        return NULL;
    }

    get_cpu_times(&prev_overall, -1);
    for (int i = 0; i < cores; ++i) get_cpu_times(&prev_cores[i], i);

    sleep(1);

    get_cpu_times(&curr_overall, -1);
    for (int i = 0; i < cores; ++i) get_cpu_times(&curr_cores[i], i);

    // compute per-core usage and overall
    size_t per_core_buf_sz = (size_t)cores * 16 + 64;
    char *per_core_buf = (char*)malloc(per_core_buf_sz);
    if (!per_core_buf) {
        free(prev_cores);
        free(curr_cores);
        return NULL;
    }
    per_core_buf[0] = '\0';
    for (int i = 0; i < cores; ++i) {
        double pct = calculate_cpu_usage(&prev_cores[i], &curr_cores[i]);
        char tmp[32];
        snprintf(tmp, sizeof(tmp), "%.2f", pct);
        if (i > 0) strncat(per_core_buf, "|", per_core_buf_sz - strlen(per_core_buf) - 1);
        strncat(per_core_buf, tmp, per_core_buf_sz - strlen(per_core_buf) - 1);
    }
    double overall_pct = calculate_cpu_usage(&prev_overall, &curr_overall);

    free(prev_cores);
    free(curr_cores);

    // memory
    long ram_total_kb = 0, ram_used_kb = 0, swap_total_kb = 0, swap_used_kb = 0;
    get_memory_info(&ram_total_kb, &ram_used_kb, &swap_total_kb, &swap_used_kb);
    double ram_pct = 0.0, swap_pct = 0.0;
    if (ram_total_kb > 0) ram_pct = (double)ram_used_kb * 100.0 / (double)ram_total_kb;
    if (swap_total_kb > 0) swap_pct = (double)swap_used_kb * 100.0 / (double)swap_total_kb;

    // disk
    double disk_total_gb = 0.0, disk_used_gb = 0.0;
    get_disk_usage(&disk_total_gb, &disk_used_gb);
    double disk_pct = 0.0;
    if (disk_total_gb > 0.0) disk_pct = (disk_used_gb * 100.0) / disk_total_gb;

    // mac
    char mac_address[64];
    get_mac_address(mac_address, sizeof(mac_address));

    // cpu temp in Celsius
    double temp_c = get_cpu_temp_c();

    // Build final string
    char *out = (char*)malloc(1024);
    if (!out) {
        free(per_core_buf);
        return NULL;
    }

    // New Format:
    // per_core|... , ram_pct , overall_cpu_pct , swap_pct , disk_pct , temp_c , mac
    snprintf(out, 1024, "%s,%.2f,%.2f,%.2f,%.2f,%.2f,%s",
             per_core_buf,
             ram_pct,
             overall_pct,
             swap_pct,
             disk_pct,
             temp_c,
             mac_address);

    free(per_core_buf);
    return out;
}

/* free() wrapper for Python/other callers */
void free_system_info_string(char *info_string) {
    if (info_string) free(info_string);
}