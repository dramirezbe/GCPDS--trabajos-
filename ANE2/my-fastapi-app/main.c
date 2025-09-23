// client.c (versión robusta: cada petición usa su propio CURL handle)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <curl/curl.h>
#include <unistd.h> // sleep
#include "cJSON.h"

struct response_string {
    char *ptr;
    size_t len;
};

void init_response_string(struct response_string *s) {
    s->len = 0;
    s->ptr = malloc(1);
    if (s->ptr == NULL) {
        fprintf(stderr, "malloc failed\n");
        exit(1);
    }
    s->ptr[0] = '\0';
}

size_t writefunc(void *ptr, size_t size, size_t nmemb, struct response_string *s) {
    size_t add = size * nmemb;
    size_t new_len = s->len + add;
    char *tmp = realloc(s->ptr, new_len + 1);
    if (tmp == NULL) {
        fprintf(stderr, "realloc failed\n");
        return 0;
    }
    s->ptr = tmp;
    memcpy(s->ptr + s->len, ptr, add);
    s->ptr[new_len] = '\0';
    s->len = new_len;
    return add;
}

/*
 * http_get: crea su propio CURL handle, realiza GET y devuelve string (malloc)
 * Caller must free() the returned pointer.
 */
char *http_get(const char *url, long timeout_secs) {
    CURL *curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "curl_easy_init() failed\n");
        return NULL;
    }

    struct response_string s;
    init_response_string(&s);

    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_HTTPGET, 1L);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writefunc);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &s);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_secs);

    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
        fprintf(stderr, "curl GET failed (%s): %s\n", url, curl_easy_strerror(res));
        free(s.ptr);
        curl_easy_cleanup(curl);
        return NULL;
    }

    curl_easy_cleanup(curl);
    return s.ptr; // caller must free()
}

/*
 * http_post_json_str: POST a url con body JSON (string). Devuelve malloc'd string con la respuesta.
 * Caller must free() the returned pointer.
 */
char *http_post_json_str(const char *url, const char *json_str, long timeout_secs) {
    CURL *curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "curl_easy_init() failed (post)\n");
        return NULL;
    }

    struct response_string s;
    init_response_string(&s);
    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    // Indicar tamaño explícito es más seguro
    curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, (long)strlen(json_str));
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_str);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, writefunc);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &s);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_secs);

    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers); // liberar header list
    if (res != CURLE_OK) {
        fprintf(stderr, "curl POST failed (%s): %s\n", url, curl_easy_strerror(res));
        free(s.ptr);
        curl_easy_cleanup(curl);
        return NULL;
    }

    curl_easy_cleanup(curl);
    return s.ptr; // caller must free()
}

/* http_post_json: toma un cJSON*, serializa y llama a http_post_json_str */
char *http_post_json(const char *url, cJSON *json, long timeout_secs) {
    if (!json) return NULL;
    char *body = cJSON_PrintUnformatted(json);
    if (!body) return NULL;
    char *resp = http_post_json_str(url, body, timeout_secs);
    free(body);
    return resp;
}

/* parsea/pretty-print JSON seguro */
void print_json_response(const char *label, const char *resp_str) {
    if (!resp_str) {
        printf("[%s] respuesta vacía\n", label);
        return;
    }
    cJSON *root = cJSON_Parse(resp_str);
    if (!root) {
        printf("[%s] respuesta no-JSON: %s\n", label, resp_str);
        return;
    }
    char *pretty = cJSON_Print(root);
    if (pretty) {
        printf("[%s] parsed JSON:\n%s\n", label, pretty);
        free(pretty);
    } else {
        printf("[%s] parsed JSON (no pretty available)\n", label);
    }
    cJSON_Delete(root);
}

int main(void) {
    const char *base = "http://127.0.0.1:8000";

    if (curl_global_init(CURL_GLOBAL_DEFAULT) != 0) {
        fprintf(stderr, "curl_global_init failed\n");
        return 1;
    }

    // GET /
    printf("[CLIENT] GET /\n");
    char *resp = http_get(base, 5L);
    print_json_response("/", resp);
    if (resp) free(resp);

    // GET /init
    printf("[CLIENT] GET /init\n");
    char init_url[256];
    snprintf(init_url, sizeof(init_url), "%s/init", base);
    resp = http_get(init_url, 5L);
    print_json_response("/init", resp);
    if (resp) free(resp);

    // POST /command startLiveData
    printf("[CLIENT] POST /command startLiveData (cJSON)\n");
    char cmd_url[256];
    snprintf(cmd_url, sizeof(cmd_url), "%s/command", base);

    cJSON *cmd_obj = cJSON_CreateObject();
    if (!cmd_obj) { fprintf(stderr, "cJSON_CreateObject failed\n"); return 1; }
    cJSON_AddStringToObject(cmd_obj, "command", "startLiveData");
    cJSON *data_obj = cJSON_CreateObject();
    cJSON_AddNumberToObject(data_obj, "freq", 1000);
    cJSON_AddNumberToObject(data_obj, "gain", 10);
    cJSON_AddItemToObject(cmd_obj, "data", data_obj);

    resp = http_post_json(cmd_url, cmd_obj, 5L);
    print_json_response("POST /command startLiveData", resp);
    if (resp) free(resp);
    cJSON_Delete(cmd_obj);

    // Poll dataStreaming varias veces
    char ds_url[256];
    snprintf(ds_url, sizeof(ds_url), "%s/dataStreaming", base);
    for (int i = 0; i < 5; ++i) {
        printf("[CLIENT] GET /dataStreaming (iter %d)\n", i+1);
        resp = http_get(ds_url, 5L);
        print_json_response("/dataStreaming", resp);
        if (resp) free(resp);
        sleep(1);
    }

    // POST /command stopLiveData
    printf("[CLIENT] POST /command stopLiveData (cJSON)\n");
    cJSON *stop_obj = cJSON_CreateObject();
    cJSON_AddStringToObject(stop_obj, "command", "stopLiveData");
    cJSON_AddItemToObject(stop_obj, "data", cJSON_CreateObject());
    resp = http_post_json(cmd_url, stop_obj, 5L);
    print_json_response("POST /command stopLiveData", resp);
    if (resp) free(resp);
    cJSON_Delete(stop_obj);

    curl_global_cleanup();
    return 0;
}
