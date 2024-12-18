import firecrawl

# Crawl operation
firecrawl.crawl(url="https://example.com", formats=["markdown", "html"])

# Scrape operation
firecrawl.scrape(url="https://example.com", formats=["markdown", "html"])

# Batch scrape operation
firecrawl.batch_scrape(urls=["https://example.com", "https://sitemaps.org"], formats=["markdown", "html"])

# Map operation
firecrawl.map(url="https://sitemaps.org")