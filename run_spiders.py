# ===============================================
# run_spiders.py - Script to Run Spiders
# ===============================================

import subprocess
import sys
import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def run_books_spider():
    """Run the books spider"""
    print("Starting Goodreads Books Spider...")

    # You can run this directly or via command line
    # Command line: scrapy crawl goodreads_books

    settings = get_project_settings()
    process = CrawlerProcess(settings)

    # Import your spider
    from goodreads_books_spider import GoodreadsBooksSpider

    process.crawl(GoodreadsBooksSpider)
    process.start()


def run_reviews_spider():
    """Run the reviews spider"""
    print("Starting Goodreads Reviews Spider...")

    # Command line: scrapy crawl goodreads_reviews

    settings = get_project_settings()
    process = CrawlerProcess(settings)

    # Import your spider
    from goodreads_reviews_spider import GoodreadsReviewsSpider

    process.crawl(GoodreadsReviewsSpider)
    process.start()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        spider_name = sys.argv[1]
        if spider_name == "books":
            run_books_spider()
        elif spider_name == "reviews":
            run_reviews_spider()
        else:
            print("Usage: python run_spiders.py [books|reviews]")
    else:
        print("Available spiders:")
        print("  books   - Scrape basic book information")
        print("  reviews - Scrape book reviews (requires Selenium)")
        print("\nUsage: python run_spiders.py [books|reviews]")
