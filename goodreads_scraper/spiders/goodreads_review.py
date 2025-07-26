import scrapy
import re
import time
import random
from urllib.parse import urljoin


class GoodreadsReviewsSpider(scrapy.Spider):
    name = "goodreads_reviews"
    allowed_domains = ["goodreads.com"]

    # Configuration
    START_ID = 1
    END_ID = 10000
    DEBUG = False

    custom_settings = {
        "FEEDS": {
            "goodreads_reviews.csv": {
                "format": "csv",
                "fields": [
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
                ],
                "overwrite": True,
            },
        },
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "ROBOTSTXT_OBEY": False,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 400, 403, 404, 408],
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    def start_requests(self):
        """Generate requests for all book IDs"""
        for book_id in range(self.START_ID, self.END_ID + 1):
            url = f"https://www.goodreads.com/book/show/{book_id}"
            yield scrapy.Request(
                url=url,
                callback=self.parse_book_page,
                meta={"book_id": book_id},
                dont_filter=True,
            )

    def parse_book_page(self, response):
        """Parse book page and extract reviews"""
        book_id = response.meta["book_id"]
        self.logger.info(f"Processing book ID: {book_id}")

        try:
            # Extract book details
            title = self.extract_book_title(response)
            author = self.extract_book_author(response)
            avg_rating = self.extract_avg_rating(response)
            ratings_count = self.extract_ratings_count(response)

            self.logger.info(f"📖 Book: {title} by {author}")
            self.logger.info(f"⭐ Avg Rating: {avg_rating} ({ratings_count} ratings)")

            # Extract reviews
            reviews = self.extract_reviews(response, book_id)

            self.logger.info(f"📝 Found {len(reviews)} reviews on the page")

            # Yield each review with book details
            for review in reviews:
                review.update(
                    {
                        "book_title": self.clean_text(title),
                        "book_author": self.clean_text(author),
                        "book_avg_rating": avg_rating,
                        "book_ratings_count": ratings_count,
                    }
                )
                yield review

            self.logger.info(f"✅ Completed book ID {book_id}: {title}")

        except Exception as e:
            self.logger.error(f"Error processing book {book_id}: {str(e)}")

    def extract_book_title(self, response):
        """Extract book title"""
        title = response.css("h1.Text__title1::text").get()
        return title or "Unknown Title"

    def extract_book_author(self, response):
        author = response.css("span.ContributorLink__name::text").get()
        return author or "Unknown Author"

    def extract_avg_rating(self, response):
        """Extract average rating"""
        rating = response.css('div[data-testid="avgRating"]::text').get()
        if not rating:
            rating = response.css("div.RatingStatistics__rating::text").get()
        return rating or "N/A"

    def extract_ratings_count(self, response):
        """Extract ratings count"""
        count = response.css('span[data-testid="ratingsCount"]::text').get()
        return count.split()[0] if count else "0"

    def extract_rating(self, rating):
        """Extract numeric rating from various string formats"""
        # Handle different rating string formats
        patterns = [
            r"(\d+\.?\d*)\s*out of \s*\d+",  # "4 out of 5"
            r"Rating\s*(\d+\.?\d*)",  # "Rating 4"
            r"(\d+\.?\d*)\s*stars?",  # "4 stars"
            r"(\d+\.?\d*)\s*/\s*\d+",  # "4/5"
            r"(\d+\.?\d*)",  # Just the number
        ]

        for pattern in patterns:
            match = re.search(pattern, rating, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue

        return None

    def extract_reviews(self, response, book_id):
        """Extract reviews from the page with guaranteed clean text"""
        reviews = []
        review_cards = response.css(".ReviewCard")

        for i, card in enumerate(review_cards):
            try:
                # Reviewer
                reviewer = card.css(".ReviewerProfile__name a::text").get()
                reviewer = reviewer or "Anonymous"

                # Rating
                rating = None
                rating_el = card.css("span.RatingStars__small::attr(aria-label)").get()
                if rating_el:
                    rating_match = re.search(
                        r"(\d+\.?\d*)\s*(?:star|out of|/|$)", rating_el
                    )
                    if rating_match:
                        rating = float(rating_match.group(1))

                # Date
                date = card.css("span.Text__body3 a::text").get()

                date = date or "Unknown date"

                # Clean up date string
                if date:
                    date = re.sub(r"\s*·\s*", "", date)  # Remove middle dots
                    date = date.strip()

                # Review text extraction
                review_text = self.extract_review_text(card)

                reviews.append(
                    {
                        "review_id": card.attrib.get("id", f"review_{book_id}_{i}"),
                        "book_id": book_id,
                        "reviewer": reviewer,
                        "rating": rating,
                        "date": date,
                        "review_text": review_text,
                    }
                )

            except Exception as e:
                self.logger.error(f"Error processing review {i + 1}: {str(e)}")
                continue

        return reviews

    def extract_review_text(self, card):
        """Robust review text extraction with multiple fallbacks"""

        # Final fallback - get all text and clean
        review_text = card.css(".ReviewText__content").get()
        return self.clean_text(review_text)

    def clean_text(self, text):
        """More thorough text cleaning"""
        if not text:
            return ""

        # Remove HTML entities and tags
        text = re.sub(r"<[^>]+>", "", text)
        # Normalize whitespace
        text = " ".join(text.split())
        # Remove control characters
        text = "".join(char for char in text if ord(char) >= 32 or ord(char) == 10)
        return text.strip()
