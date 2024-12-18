from .validators import ValidationError, ResponseValidationError
import requests
import yaml

class FirecrawlError(Exception):
    pass

class ConfigurationError(FirecrawlError):
    pass

class APIError(FirecrawlError):
    pass

class NetworkError(FirecrawlError):
    pass

class ResponseError(FirecrawlError):
    pass

class ErrorHandler:
    def __init__(self):
        self.HTTP_ERROR_MESSAGES = {
            400: "Bad request: The server could not process the request due to invalid parameters",
            401: "Unauthorized: Invalid or missing API key",
            402: "Payment required: Please check your subscription status",
            403: "Forbidden: You don't have permission to access this resource",
            404: "Not found: The requested resource could not be found",
            429: "Rate limit exceeded: Please try again later",
            500: "Internal server error: Please try again later",
            502: "Bad gateway: The server received an invalid response",
            503: "Service unavailable: The server is temporarily down",
            504: "Gateway timeout: The server took too long to respond"
        }

    def handle_configuration_error(self, error):
        if isinstance(error, FileNotFoundError):
            raise ConfigurationError("Configuration file not found: Please ensure config.yaml exists")
        elif isinstance(error, yaml.YAMLError):
            raise ConfigurationError(f"Invalid YAML configuration: {str(error)}")
        elif isinstance(error, KeyError):
            raise ConfigurationError(f"Missing configuration key: {str(error)}")
        elif isinstance(error, ValueError) and "FIRECRAWL_API_KEY" in str(error):
            raise ConfigurationError("API key not found: Please set the FIRECRAWL_API_KEY environment variable")
        else:
            raise ConfigurationError(f"Configuration error: {str(error)}")

    def handle_validation_error(self, error):
        if isinstance(error, ValidationError):
            raise FirecrawlError(f"Validation error: {str(error)}")
        elif isinstance(error, ResponseValidationError):
            raise ResponseError(f"Response validation error: {str(error)}")

    def handle_network_error(self, error):
        if isinstance(error, requests.ConnectionError):
            raise NetworkError("Unable to connect to the API: Please check your internet connection")
        elif isinstance(error, requests.Timeout):
            raise NetworkError("Request timed out: The server took too long to respond")
        elif isinstance(error, requests.RequestException):
            raise NetworkError(f"Network error: {str(error)}")

    def handle_http_error(self, status_code, response_body=None):
        error_message = self.HTTP_ERROR_MESSAGES.get(
            status_code,
            f"Unexpected HTTP error occurred: Status code {status_code}"
        )
        
        if response_body:
            if isinstance(response_body, dict):
                error = response_body.get('error', {})
                if isinstance(error, dict):
                    error_detail = error.get('message', '')
                else:
                    error_detail = str(error)
            else:
                error_detail = str(response_body)
                
            if error_detail:
                error_message = f"{error_message} - {error_detail}"

        if 400 <= status_code < 500:
            raise APIError(error_message)
        else:
            raise NetworkError(error_message)

    def handle_response_error(self, error, endpoint=None):
        if isinstance(error, (dict, str)):
            error_message = str(error)
        else:
            error_message = f"Error processing response from {endpoint}: {str(error)}"
        raise ResponseError(error_message)

    def handle_operation_error(self, operation, error):
        operation_name = operation.capitalize() if operation else "Operation"
        if isinstance(error, (ValidationError, ResponseValidationError)):
            self.handle_validation_error(error)
        elif isinstance(error, requests.RequestException):
            self.handle_network_error(error)
        elif isinstance(error, (ConfigurationError, APIError, NetworkError, ResponseError)):
            raise error
        else:
            raise FirecrawlError(f"{operation_name} failed: {str(error)}")

    def validate_response(self, response, expected_fields=None):
        if not isinstance(response, dict):
            raise ResponseError("Invalid response format: Expected a dictionary")
        
        if expected_fields:
            missing_fields = [field for field in expected_fields if field not in response]
            if missing_fields:
                raise ResponseError(f"Missing required fields in response: {', '.join(missing_fields)}")
        
        if 'error' in response:
            error_message = response['error'].get('message', 'Unknown error occurred')
            raise ResponseError(f"API returned an error: {error_message}")

    def handle_retry_timeout(self, retries, max_retries, operation=None):
        operation_name = operation.capitalize() if operation else "Operation"
        raise TimeoutError(
            f"{operation_name} timed out after {retries} retries (max: {max_retries}). "
            "The operation might still be processing on the server."
        )