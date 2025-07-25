# Goodreads Scraper

This repository contains two Python scripts for scraping book data and reviews from Goodreads.

## Scripts

### 1. `get_books.py`

Scrapes basic book information from Goodreads by iterating through book IDs.

**Features:**
- Scrapes book details including title, author, ratings, ISBN, publisher, and genres
- Handles missing data gracefully
- Includes random delays between requests to avoid rate limiting
- Saves data to a CSV file (`goodreads_books.csv`)

**Usage:**
```bash
python get_books.py
```

### 2. `get_reviews.py`

Scrapes book reviews using Selenium to handle JavaScript-rendered content.

**Features:**
- Uses Selenium with Chrome WebDriver for dynamic content
- Expands truncated reviews automatically
- Scrapes reviewer names, ratings, dates, and full review text
- Includes anti-detection measures (random delays, incognito mode)
- Saves data to a CSV file (`output/goodreads_reviews.csv`)

**Usage:**
```bash
python get_reviews.py
```

## Requirements

- Python 3.x
- Required packages:
  ```
  requests
  beautifulsoup4
  selenium
  ```

## Configuration

Both scripts include configurable parameters at the top of the file:
- ID ranges to scrape
- Delay timings
- Output file locations
- Debug options

## Notes

- For educational purpose only!, please use responsibly and respect Goodreads' terms of service
- Consider adding longer delays if scraping large amounts of data
