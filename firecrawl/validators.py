from urllib.parse import urlparse

class ValidationError(Exception):
    pass

class ResponseValidationError(Exception):
    pass

class FirecrawlValidator:
    def __init__(self):
        self.AVAILABLE_FORMATS = ["markdown", "html", "rawHtml", "links", "extract", "screenshot", "screenshot@fullPage"]
        self.AVAILABLE_ACTION_TYPES = ["wait", "screenshot", "click", "write", "press", "scroll", "scrape"]
        self.SCROLL_DIRECTIONS = ["up", "down"]
    
    def validate_url(self, url):
        if not isinstance(url, str):
            raise ValidationError("URL must be a string")
        
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValidationError("Invalid URL format")
        except Exception:
            raise ValidationError("Invalid URL format")
    
    def validate_url_list(self, urls):
        if not isinstance(urls, list):
            raise ValidationError("URLs must be provided as a list")
        if not urls:
            raise ValidationError("URLs list cannot be empty")
        for url in urls:
            self.validate_url(url)
    
    def validate_formats(self, formats):
        if not isinstance(formats, list):
            raise ValidationError("Formats must be provided as a list")
        if not formats:
            raise ValidationError("At least one format must be specified")
        invalid_formats = set(formats) - set(self.AVAILABLE_FORMATS)
        if invalid_formats:
            raise ValidationError(f"Invalid formats: {list(invalid_formats)}. Available formats: {self.AVAILABLE_FORMATS}")

    def validate_response_format(self, format_name):
        if format_name not in self.AVAILABLE_FORMATS:
            raise ResponseValidationError(f"Invalid format in response: {format_name}")
        return True

    def get_response_formats(self, data_item):
        if not isinstance(data_item, dict):
            raise ResponseValidationError("Response data item must be a dictionary")
        
        formats = []
        for key in data_item.keys():
            try:
                if self.validate_response_format(key):
                    formats.append(key)
            except ResponseValidationError:
                continue
        return formats
    
    def validate_boolean(self, value, field_name):
        if not isinstance(value, bool):
            raise ValidationError(f"{field_name} must be a boolean")
    
    def validate_integer(self, value, field_name, min_value=None, max_value=None):
        if not isinstance(value, int):
            raise ValidationError(f"{field_name} must be an integer")
        if min_value is not None and value < min_value:
            raise ValidationError(f"{field_name} must be greater than or equal to {min_value}")
        if max_value is not None and value > max_value:
            raise ValidationError(f"{field_name} must be less than or equal to {max_value}")
    
    def validate_string_array(self, value, field_name):
        if not isinstance(value, list):
            raise ValidationError(f"{field_name} must be a list")
        if not all(isinstance(item, str) for item in value):
            raise ValidationError(f"All items in {field_name} must be strings")
    
    def validate_object(self, value, field_name):
        if not isinstance(value, dict):
            raise ValidationError(f"{field_name} must be an object")
    
    def validate_action(self, action):
        if not isinstance(action, dict):
            raise ValidationError("Action must be an object")
        
        if "type" not in action:
            raise ValidationError("Action must have a type")
        
        if action["type"] not in self.AVAILABLE_ACTION_TYPES:
            raise ValidationError(f"Invalid action type. Available types: {self.AVAILABLE_ACTION_TYPES}")
        
        if action["type"] == "wait":
            if "milliseconds" in action:
                self.validate_integer(action["milliseconds"], "milliseconds", min_value=0)
            if "selector" in action:
                self.validate_string_array([action["selector"]], "selector")
                
        elif action["type"] == "screenshot":
            if "fullPage" in action:
                self.validate_boolean(action["fullPage"], "fullPage")
                
        elif action["type"] in ["click", "write"]:
            if "selector" not in action:
                raise ValidationError(f"{action['type']} action requires a selector")
            self.validate_string_array([action["selector"]], "selector")
            
            if action["type"] == "write" and "text" not in action:
                raise ValidationError("write action requires text")
                
        elif action["type"] == "press":
            if "key" not in action:
                raise ValidationError("press action requires a key")
            self.validate_string_array([action["key"]], "key")
            
        elif action["type"] == "scroll":
            if "direction" not in action:
                raise ValidationError("scroll action requires a direction")
            if action["direction"] not in self.SCROLL_DIRECTIONS:
                raise ValidationError(f"Invalid scroll direction. Available directions: {self.SCROLL_DIRECTIONS}")
            if "amount" in action:
                self.validate_integer(action["amount"], "amount", min_value=1)

    def validate_location(self, location):
        if not isinstance(location, dict):
            raise ValidationError("Location must be an object")
            
        if "country" in location:
            if not isinstance(location["country"], str) or len(location["country"]) != 2:
                raise ValidationError("Country must be an ISO 3166-1 alpha-2 country code")
                
        if "languages" in location:
            self.validate_string_array(location["languages"], "languages")

    def validate_extract(self, extract):
        if not isinstance(extract, dict):
            raise ValidationError("Extract must be an object")
            
        if "schema" in extract:
            self.validate_object(extract["schema"], "schema")
            
        for field in ["systemPrompt", "prompt"]:
            if field in extract:
                if not isinstance(extract[field], str):
                    raise ValidationError(f"{field} must be a string")


class RequestValidator:
    def __init__(self):
        self.validator = FirecrawlValidator()

    def validate_crawl_request(self, params):
        required_fields = ["url"]
        for field in required_fields:
            if field not in params:
                raise ValidationError(f"Missing required field: {field}")
        
        self.validator.validate_url(params["url"])
        
        if "excludePaths" in params:
            self.validator.validate_string_array(params["excludePaths"], "excludePaths")
            
        if "includePaths" in params:
            self.validator.validate_string_array(params["includePaths"], "includePaths")
            
        if "maxDepth" in params:
            self.validator.validate_integer(params["maxDepth"], "maxDepth", min_value=1)
            
        if "ignoreSitemap" in params:
            self.validator.validate_boolean(params["ignoreSitemap"], "ignoreSitemap")
            
        if "limit" in params:
            self.validator.validate_integer(params["limit"], "limit", min_value=1, max_value=10000)
            
        if "allowBackwardLinks" in params:
            self.validator.validate_boolean(params["allowBackwardLinks"], "allowBackwardLinks")
            
        if "allowExternalLinks" in params:
            self.validator.validate_boolean(params["allowExternalLinks"], "allowExternalLinks")
            
        if "webhook" in params:
            self.validator.validate_url(params["webhook"])
            
        if "scrapeOptions" in params:
            self.validator.validate_object(params["scrapeOptions"], "scrapeOptions")
            options = params["scrapeOptions"]
            
            if "formats" in options:
                self.validator.validate_formats(options["formats"])
                
            if "headers" in options:
                self.validator.validate_object(options["headers"], "headers")
                
            if "includeTags" in options:
                self.validator.validate_string_array(options["includeTags"], "includeTags")
                
            if "excludeTags" in options:
                self.validator.validate_string_array(options["excludeTags"], "excludeTags")
                
            if "onlyMainContent" in options:
                self.validator.validate_boolean(options["onlyMainContent"], "onlyMainContent")
                
            if "mobile" in options:
                self.validator.validate_boolean(options["mobile"], "mobile")
                
            if "waitFor" in options:
                self.validator.validate_integer(options["waitFor"], "waitFor", min_value=0)

    def validate_scrape_request(self, params):
        required_fields = ["url"]
        for field in required_fields:
            if field not in params:
                raise ValidationError(f"Missing required field: {field}")
        
        self.validator.validate_url(params["url"])
        
        if "formats" in params:
            self.validator.validate_formats(params["formats"])
            
        if "onlyMainContent" in params:
            self.validator.validate_boolean(params["onlyMainContent"], "onlyMainContent")
            
        if "includeTags" in params:
            self.validator.validate_string_array(params["includeTags"], "includeTags")
            
        if "excludeTags" in params:
            self.validator.validate_string_array(params["excludeTags"], "excludeTags")
            
        if "headers" in params:
            self.validator.validate_object(params["headers"], "headers")
            
        if "waitFor" in params:
            self.validator.validate_integer(params["waitFor"], "waitFor", min_value=0)
            
        if "mobile" in params:
            self.validator.validate_boolean(params["mobile"], "mobile")
            
        if "skipTlsVerification" in params:
            self.validator.validate_boolean(params["skipTlsVerification"], "skipTlsVerification")
            
        if "timeout" in params:
            self.validator.validate_integer(params["timeout"], "timeout", min_value=1000)
            
        if "extract" in params:
            self.validator.validate_extract(params["extract"])
            
        if "actions" in params:
            if not isinstance(params["actions"], list):
                raise ValidationError("Actions must be an array")
            for action in params["actions"]:
                self.validator.validate_action(action)
                
        if "location" in params:
            self.validator.validate_location(params["location"])

    def validate_batch_scrape_request(self, params):
        required_fields = ["urls"]
        for field in required_fields:
            if field not in params:
                raise ValidationError(f"Missing required field: {field}")
        
        self.validator.validate_url_list(params["urls"])
        
        if "formats" in params:
            self.validator.validate_formats(params["formats"])
            
        if "onlyMainContent" in params:
            self.validator.validate_boolean(params["onlyMainContent"], "onlyMainContent")
            
        if "includeTags" in params:
            self.validator.validate_string_array(params["includeTags"], "includeTags")
            
        if "excludeTags" in params:
            self.validator.validate_string_array(params["excludeTags"], "excludeTags")
            
        if "headers" in params:
            self.validator.validate_object(params["headers"], "headers")
            
        if "waitFor" in params:
            self.validator.validate_integer(params["waitFor"], "waitFor", min_value=0)
            
        if "timeout" in params:
            self.validator.validate_integer(params["timeout"], "timeout", min_value=1000)
            
        if "extract" in params:
            self.validator.validate_extract(params["extract"])
            
        if "actions" in params:
            if not isinstance(params["actions"], list):
                raise ValidationError("Actions must be an array")
            for action in params["actions"]:
                self.validator.validate_action(action)

    def validate_map_request(self, params):
        required_fields = ["url"]
        for field in required_fields:
            if field not in params:
                raise ValidationError(f"Missing required field: {field}")
        
        self.validator.validate_url(params["url"])
        
        if "search" in params:
            if not isinstance(params["search"], str):
                raise ValidationError("Search must be a string")
                
        if "ignoreSitemap" in params:
            self.validator.validate_boolean(params["ignoreSitemap"], "ignoreSitemap")
            
        if "includeSubdomains" in params:
            self.validator.validate_boolean(params["includeSubdomains"], "includeSubdomains")
            
        if "limit" in params:
            self.validator.validate_integer(params["limit"], "limit", min_value=1, max_value=5000)

    def validate_id(self, id):
        if not isinstance(id, str):
            raise ValidationError("ID must be a string")
        if not id.strip():
            raise ValidationError("ID cannot be empty")