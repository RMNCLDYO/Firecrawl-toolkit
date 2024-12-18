from .error_handler import ConfigurationError, APIError, NetworkError, ResponseError
from .main import FirecrawlAPI

class RunFirecrawlAPI:
    def __init__(self):
        self.api = FirecrawlAPI()

    def _print_status(self, status_info, show_progress):
        if status_info and show_progress:
            for info in status_info:
                if info["status"] == "scraping":
                    print(f"TASK STATUS: In progress... (attempt {info['retries'] + 1})")

    def _print_response(self, formatted_response):
        has_output = False

        if "data" in formatted_response and formatted_response["data"]:
            has_output = True
            for data_item in formatted_response["data"]:
                for format_type, content in data_item.items():
                    format_header = format_type.upper()
                    if content["type"] == "markdown":
                        print(f"\n{format_header}:\n```markdown\n{content['content']}\n```")
                    elif content["type"] == "html":
                        print(f"\n{format_header}:\n```html\n{content['content']}\n```")
                    else:
                        print(f"\n{format_header}:\n```\n{content['content']}\n```")

        if "links" in formatted_response and formatted_response["links"]:
            has_output = True
            print("\nLINKS:")
            for link in formatted_response["links"]:
                print(link)
        
        if "status_info" in formatted_response:
            self._print_status(formatted_response["status_info"], not has_output)

        if not has_output:
            print(f"\nTASK STATUS: {formatted_response['status']}")

    def _run_firecrawl(self, operation_name, *args, **kwargs):
        try:
            print(f"TASK STATUS: Starting {operation_name}...")
            
            operation = getattr(self.api, operation_name)
            response = operation(*args, **kwargs)
            
            processed_response = self.api.get_response_with_retries(
                initial_response=response[0],
                endpoint=response[1]
            )
            
            if processed_response:
                formatted_response = self.api.format_response_data(processed_response)
                self._print_response(formatted_response)
                print(f"\nTASK STATUS: {operation_name} completed successfully!")
                return processed_response
                
        except (ConfigurationError, APIError, NetworkError, ResponseError) as e:
            print(f"Error: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise

    def crawl(self, url, **kwargs):
        return self._run_firecrawl('crawl', url=url, **kwargs)

    def scrape(self, url, **kwargs):
        return self._run_firecrawl('scrape', url=url, **kwargs)
    
    def batch_scrape(self, urls, **kwargs):
        return self._run_firecrawl('batch_scrape', urls=urls, **kwargs)

    def map(self, url, **kwargs):
        return self._run_firecrawl('map', url=url, **kwargs)

firecrawl_runner = RunFirecrawlAPI()

crawl = firecrawl_runner.crawl
scrape = firecrawl_runner.scrape
batch_scrape = firecrawl_runner.batch_scrape
map = firecrawl_runner.map