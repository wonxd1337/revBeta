# config.py
import os
import tempfile

class Config:
    # ========== THREAD SETTINGS ==========
    MAX_THREADS_REVERSE = 30
    MAX_THREADS_SCAN = 100
    
    # ========== PROXY SETTINGS ==========
    PROXY_SOURCES = [
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/all/data.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    ]
    
    PROXY_REFRESH_INTERVAL = 1800
    PROXY_MAX_FAILURES = 5
    PROXY_MIN_WEIGHT = 0.1
    PROXY_MAX_WEIGHT = 3.0
    PROXY_MAX_TOTAL = 500
    
    # ========== RNG SETTINGS ==========
    MAX_VALID_RNG = 50
    MAX_VALID_RNG_LIMIT = 200
    
    # ========== CACHE SETTINGS ==========
    MAX_CACHE_SIZE = 10000
    CACHE_CLEANUP_INTERVAL = 3600
    
    # ========== MEMORY MANAGEMENT ==========
    TEMP_DIR = tempfile.gettempdir() + "/mt_scanner/"
    MAX_MEMORY_ITEMS = 5000
    
    # ========== FILE OUTPUT ==========
    OUTPUT_FILES = {
        'movable_type': 'movable_type.txt',
        'movable_type_v4': 'movable_type_v4.txt',
        'processed_ips': 'processed_ips.txt',
        'cache': 'cache.db'
    }
    
    # ========== REQUEST SETTINGS ==========
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    TIMEOUT_REVERSE = 30    # ← HANYA INI YANG DITAMBAH
    TIMEOUT_SCAN = 10       # ← DAN INI
    
    # ========== DEBUG MODE ==========
    DEBUG = False
    
    @staticmethod
    def ensure_temp_dir():
        if not os.path.exists(Config.TEMP_DIR):
            os.makedirs(Config.TEMP_DIR)
