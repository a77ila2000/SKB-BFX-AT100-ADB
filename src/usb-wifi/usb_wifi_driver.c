/* USB bus drivers remain registered across Wi-Fi off/on. The HAL owns STA state. */
extern unsigned int if_nametoindex(const char *name);

int is_wifi_driver_loaded(void) {
    return if_nametoindex("wlan0") != 0;
}

int wifi_load_driver(void) {
    return is_wifi_driver_loaded() ? 0 : -1;
}

int wifi_unload_driver(void) {
    return 0;
}
