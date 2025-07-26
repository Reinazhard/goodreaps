# Goodreads Reviews Scraper

A Python Scrapy spider to extract book reviews from Goodreads.

## Features

- Extracts book details (title, author, average rating)
- Collects individual reviews with:
  - Reviewer name
  - Star rating (converted to numeric value)
  - Review date
  - Full review text

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install scrapy beautifulsoup4 lxml
   ```

## Usage

Run the spider with:
```bash
scrapy crawl goodreads_[books/reviews]
```

### Configuration Options

Edit these variables in `goodreads_[books/reviews].py`:
- `START_ID`: Starting book ID (default: 1)
- `END_ID`: Ending book ID (default: 10)

## Output

Results are saved to `goodreads_[books/reviews].csv` with these columns:
- Review ID
- Book ID
- Reviewer name
- Rating (as float)
- Review date
- Review text
- Book title
- Book author
- Book average rating
- Book ratings count

## Notes

- For educational purpose only!
- Please use responsibly and respect Goodreads' terms of service
