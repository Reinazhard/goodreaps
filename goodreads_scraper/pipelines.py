# ===============================================
# pipelines.py - Data Processing Pipeline
# ===============================================

import os
import csv
from datetime import datetime
from itemadapter import ItemAdapter


class GoodreadsScraperPipeline:
    """Pipeline for processing scraped Goodreads data"""

    def __init__(self):
        self.files = {}
        self.writers = {}

    def open_spider(self, spider):
        """Initialize files and writers for each spider"""
        if spider.name == "goodreads_books":
            self.setup_books_pipeline(spider)
        elif spider.name == "goodreads_reviews":
            self.setup_reviews_pipeline(spider)

    def setup_books_pipeline(self, spider):
        """Setup pipeline for books spider"""
        filename = "goodreads_books.csv"
        self.files[spider.name] = open(filename, "w", newline="", encoding="utf-8")

        fieldnames = [
            "book_id",
            "url",
            "title",
            "author",
            "avg_rating",
            "ratings_count",
            "reviews_count",
            "isbn",
            "pages",
            "publisher",
            "genres",
            "scraped_at",
        ]

        self.writers[spider.name] = csv.DictWriter(
            self.files[spider.name], fieldnames=fieldnames
        )
        self.writers[spider.name].writeheader()

    def setup_reviews_pipeline(self, spider):
        """Setup pipeline for reviews spider"""
        filename = "goodreads_reviews.csv"
        self.files[spider.name] = open(filename, "w", newline="", encoding="utf-8")

        fieldnames = [
            "review_id",
            "book_id",
            "reviewer",
            "rating",
            "date",
            "review_text",
            "book_title",
            "book_author",
            "book_avg_rating",
            "book_ratings_count",
        ]

        self.writers[spider.name] = csv.DictWriter(
            self.files[spider.name], fieldnames=fieldnames
        )
        self.writers[spider.name].writeheader()

    def process_item(self, item, spider):
        """Process each scraped item"""
        adapter = ItemAdapter(item)

        # Write to CSV
        if spider.name in self.writers:
            self.writers[spider.name].writerow(dict(adapter))

        return item

    def close_spider(self, spider):
        """Clean up when spider closes"""
        if spider.name in self.files:
            self.files[spider.name].close()
            spider.logger.info(f"Results saved to CSV file")
