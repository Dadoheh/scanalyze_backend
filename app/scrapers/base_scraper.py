import abc
import asyncio
import logging
import httpx
import time
import random
from typing import Any, Dict, List, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class BaseScraper(abc.ABC):
    """Base abstract class for all scrapers."""
    
    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize the scraper with an optional rate limit.
        
        :param rate_limit: Minimum time in seconds between requests.
        """
        self.rate_limit = rate_limit
        self.last_request_time = 0.0
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        
    async def _make_request(self, url: str, method: str = 'GET', 
                            headers: Optional[Dict[str, str]] = None,
                            params: Optional[Dict[str, Any]] = None,
                            json_data: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """
        Make a rate-limited HTTP request.
        
        Args:
            url: URL to request
            method: HTTP method
            headers: Request headers
            params: URL parameters
            json_data: JSON data to send
            
        Returns:
            HTTP response object
        """
        
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.rate_limit:
            delay = self.rate_limit - elapsed + random.uniform(0.1, 0.3)  # Add jitter
            logger.debug(f"Rate limiting: sleeping for {delay:.2f} seconds")
            await asyncio.sleep(delay)
        
        self.last_request_time = time.time()
        
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=headers, params=params, json=json_data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=f"External API error: {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise HTTPException(status_code=503, detail=f"External API unavailable: {str(e)}")

    @abc.abstractmethod
    async def search_by_name(self, name: str) -> Dict[str, Any]:
        """
        Search for an ingredient by name.
        
        Args:
            name: Ingredient name to search
            
        Returns:
            Dictionary with ingredient data
        """
        pass
    
    @abc.abstractmethod
    async def search_by_cas(self, cas_number: str) -> Dict[str, Any]:
        """
        Search for an ingredient by CAS number.
        
        Args:
            cas_number: CAS registry number
            
        Returns:
            Dictionary with ingredient data
        """
        pass
    