from agno.tools import Toolkit
from agno.utils.log import logger
from typing import Dict, Any, Optional, List
import os
import requests
import json

class SimplifiedMapTools(Toolkit):
    """A simplified version of Google Maps tools that avoids complex schema issues."""
    
    def __init__(self):
        super().__init__(name="simplified_maps")
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not found in environment")
        
        # Register functions
        self.register(self.search_places)
    
    def search_places(self, query: str) -> str:
        """
        Search for places using Google Maps Places API.
        
        Args:
            query (str): Search query for places
            
        Returns:
            str: JSON string with place results
        """
        if not self.api_key:
            return "Error: Google Maps API key is not configured."
        
        try:
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                "query": query,
                "key": self.api_key
            }
            
            response = requests.get(url, params=params)
            results = response.json()
            
            if results.get("status") != "OK":
                return f"Error searching Google Maps: {results.get('status')} ({results.get('error_message', 'No error message provided')})"
            
            # Process and simplify the results
            places = []
            for place in results.get("results", [])[:10]:  # Limit to 10 results
                place_details = {
                    "name": place.get("name", "Unknown"),
                    "address": place.get("formatted_address", "No address"),
                    "rating": place.get("rating", 0),
                    "total_ratings": place.get("user_ratings_total", 0),
                    "type": ", ".join(place.get("types", ["Unknown"])),
                }
                places.append(place_details)
            
            return json.dumps(places, indent=2)
            
        except Exception as e:
            logger.error(f"Error in search_places: {str(e)}")
            return f"Error searching places: {str(e)}"
