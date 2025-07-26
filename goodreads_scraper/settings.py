# ===============================================
# settings.py - Scrapy Project Settings
# ===============================================

BOT_NAME = "goodreads_scraper"

SPIDER_MODULES = ["goodreads_scraper.spiders"]
NEWSPIDER_MODULE = "goodreads_scraper.spiders"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# Configure delays for requests
DOWNLOAD_DELAY = 1.5
RANDOMIZE_DOWNLOAD_DELAY = 0.5

# AutoThrottle settings
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = "httpcache"

# Default request headers
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
}

# Configure pipelines
ITEM_PIPELINES = {
    "goodreads_scraper.pipelines.GoodreadsScraperPipeline": 300,
}

# Retry settings
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]

# Log level
LOG_LEVEL = "INFO"

# Enable stats collection
STATS_CLASS = "scrapy.statscollectors.MemoryStatsCollector"

# Set settings whose default value is deprecated
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
