from .error_handler import ErrorHandler, ConfigurationError, ResponseError
from .validators import RequestValidator, FirecrawlValidator
from dotenv import load_dotenv
import requests
import yaml
import time
import os

class FirecrawlAPI:
    def __init__(self):
        self.error_handler = ErrorHandler()
        self.validator = FirecrawlValidator()
        self.request_validator = RequestValidator()
        try:
            self.config_data = self.load_config()
        except Exception as e:
            self.error_handler.handle_configuration_error(e)

    def load_config(self):
        load_dotenv()
        API_KEY = os.getenv("FIRECRAWL_API_KEY")
        if not API_KEY:
            raise ValueError("FIRECRAWL_API_KEY not found in environment variables.")

        try:
            with open("config.yaml", "r") as file:
                config = yaml.safe_load(file)

            BASE_URL = config["config"]["base_url"]
            API_VERSION = config["config"]["api_version"]
            ENDPOINTS = config["config"]["endpoints"]
            HEADERS = config["config"]["headers"]
            HEADERS.update({"Authorization": f"Bearer {API_KEY}"})

            return {
                "headers": HEADERS,
                "endpoints": {
                    "crawl": f"{BASE_URL}/{API_VERSION}/{ENDPOINTS['crawl_endpoint']}",
                    "scrape": f"{BASE_URL}/{API_VERSION}/{ENDPOINTS['scrape_endpoint']}",
                    "map": f"{BASE_URL}/{API_VERSION}/{ENDPOINTS['map_endpoint']}",
                    "batch_scrape": f"{BASE_URL}/{API_VERSION}/{ENDPOINTS['batch_scrape_endpoint']}",
                    "get_crawl_status": f"{BASE_URL}/{API_VERSION}/{ENDPOINTS['crawl_endpoint']}/{{id}}",
                    "cancel_crawl": f"{BASE_URL}/{API_VERSION}/{ENDPOINTS['crawl_endpoint']}/{{id}}",
                    "get_batch_scrape_status": f"{BASE_URL}/{API_VERSION}/{ENDPOINTS['batch_scrape_endpoint']}/{{id}}"
                }
            }
        except Exception as e:
            self.error_handler.handle_configuration_error(e)

    def make_request(self, method=None, endpoint=None, payload=None, id=None):
        url = self.config_data["endpoints"].get(endpoint)
        if not url:
            raise ConfigurationError(f"URL for '{endpoint}' not found.")

        url = url if not id else url.format(id=id)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.config_data["headers"],
                json=payload
            )
            
            try:
                response_data = response.json()
            except (ValueError, requests.exceptions.JSONDecodeError):
                response_data = response.text

            if response.status_code != 200:
                self.error_handler.handle_http_error(response.status_code, response_data)
            
            if isinstance(response_data, str):
                raise ResponseError("Expected JSON response but got string")
                
            self.error_handler.validate_response(response_data)
            return response_data, endpoint
            
        except requests.RequestException as e:
            self.error_handler.handle_network_error(e)

    def crawl(self, url=None, **kwargs):
        try:
            self.request_validator.validate_crawl_request({
                "url": url,
                **kwargs,
                "scrapeOptions": {"formats": kwargs.get('formats', [])}
            })
            
            kwargs['scrapeOptions'] = {"formats": kwargs.pop('formats', [])}
            payload = {"url": url, **kwargs}
            
            response = self.make_request(method="POST", endpoint="crawl", payload=payload)
            return response
            
        except Exception as e:
            self.error_handler.handle_operation_error("crawl", e)

    def scrape(self, url=None, **kwargs):
        try:
            self.request_validator.validate_scrape_request({
                "url": url,
                **kwargs
            })
            
            response = self.make_request(
                method="POST",
                endpoint="scrape",
                payload={"url": url, **kwargs}
            )
            return response
            
        except Exception as e:
            self.error_handler.handle_operation_error("scrape", e)

    def batch_scrape(self, urls=None, **kwargs):
        try:
            self.request_validator.validate_batch_scrape_request({
                "urls": urls,
                **kwargs
            })
            
            response = self.make_request(
                method="POST",
                endpoint="batch_scrape",
                payload={"urls": urls, **kwargs}
            )
            return response
            
        except Exception as e:
            self.error_handler.handle_operation_error("batch scrape", e)

    def map(self, url=None, **kwargs):
        try:
            self.request_validator.validate_map_request({
                "url": url,
                **kwargs
            })
            
            response = self.make_request(
                method="POST",
                endpoint="map",
                payload={"url": url, **kwargs}
            )
            return response
            
        except Exception as e:
            self.error_handler.handle_operation_error("map", e)

    def get_crawl_status(self, id):
        try:
            self.request_validator.validate_id(id)
            return self.make_request(method="GET", endpoint="get_crawl_status", id=id)
        except Exception as e:
            self.error_handler.handle_operation_error("get crawl status", e)

    def cancel_crawl(self, id):
        try:
            self.request_validator.validate_id(id)
            return self.make_request(method="DELETE", endpoint="cancel_crawl", id=id)
        except Exception as e:
            self.error_handler.handle_operation_error("cancel crawl", e)

    def get_batch_scrape_status(self, id):
        try:
            self.request_validator.validate_id(id)
            return self.make_request(method="GET", endpoint="get_batch_scrape_status", id=id)
        except Exception as e:
            self.error_handler.handle_operation_error("get batch scrape status", e)

    def get_response_with_retries(self, initial_response=None, endpoint=None, max_retries=10, delay=2):
        try:
            response = initial_response
            
            if endpoint not in ["crawl", "batch_scrape"]:
                return response
                
            if not response.get("success"):
                return response
                
            id = response.get("id")
            if not id:
                self.error_handler.handle_response_error(f"{endpoint} response missing ID field")

            retries = 0
            status_info = []
            while retries < max_retries:
                try:
                    if endpoint == "crawl":
                        response_tuple = self.get_crawl_status(id=id)
                    else:
                        response_tuple = self.get_batch_scrape_status(id=id)

                    response = response_tuple[0]
                    
                    if "status" not in response:
                        self.error_handler.handle_response_error("Response missing status field")
                        
                    status = response.get("status")
                    status_info.append({"status": status, "retries": retries})
                    
                    if status == "completed":
                        break
                    elif status == "scraping":
                        time.sleep(delay)
                    elif status == "failed":
                        self.error_handler.handle_response_error(f"Request failed with status: {status}")
                    
                    retries += 1
                    
                    if retries >= max_retries:
                        self.error_handler.handle_retry_timeout(retries, max_retries, endpoint)
                        
                except Exception as e:
                    self.error_handler.handle_operation_error(f"get {endpoint} status", e)
                    break

            response['status_info'] = status_info
            return response
            
        except Exception as e:
            self.error_handler.handle_operation_error("get response", e)

    def format_response_data(self, response):
        try:
            formatted_output = {
                "data": [],
                "links": [],
                "status": "Processing request..."
            }

            if "data" in response:
                data = response.get("data")
                if isinstance(data, dict):
                    data = [data]

                for data_item in data:
                    formatted_item = {}
                    formats = self.validator.get_response_formats(data_item)
                    for format in formats:
                        content = data_item.get(format)
                        if content:
                            formatted_item[format] = {
                                "content": content,
                                "type": "markdown" if format == "markdown" else "html" if format in ["html", "rawHtml"] else "text"
                            }
                    if formatted_item:
                        formatted_output["data"].append(formatted_item)
                        
            elif "links" in response:
                links = response.get("links", [])
                if links:
                    formatted_output["links"] = links
                    formatted_output["status"] = "Links available"
                else:
                    formatted_output["status"] = "No links available in response."
            
            if "status_info" in response:
                formatted_output["status_info"] = response["status_info"]
                
            return formatted_output
                
        except Exception as e:
            self.error_handler.handle_operation_error("format response", e)