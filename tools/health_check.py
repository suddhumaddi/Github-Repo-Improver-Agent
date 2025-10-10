import os
import requests
import logging

logger = logging.getLogger("HealthCheck")

def check_openrouter_api_health(api_key: str) -> bool:
    """
    Performs a simple health check by hitting the OpenRouter API endpoint.
    This verifies both connectivity and API key validity.
    """
    if not api_key:
        logger.error("Health check failed: OPENROUTER_API_KEY is missing.")
        return False

    # Using the standard API endpoint to check service status
    url = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1") + "/models"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        # Explicit timeout for the health check itself (5 seconds)
        response = requests.get(url, headers=headers, timeout=5) 
        
        if response.status_code == 200:
            logger.info("OpenRouter API Health Check: SUCCESS (200 OK).")
            return True
        else:
            logger.error(f"OpenRouter API Health Check: FAILED. Status Code: {response.status_code}")
            logger.error(f"API key may be invalid or expired. Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("OpenRouter API Health Check: TIMEOUT after 5s. Network likely unstable.")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenRouter API Health Check: CONNECTION ERROR. Error: {e}")
        return False