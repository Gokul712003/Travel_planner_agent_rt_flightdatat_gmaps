import json
import logging
from datetime import datetime, timedelta
from amadeus import Client, ResponseError
from typing import Optional, Dict, Any, List
from agno.tools import Toolkit
from agno.utils.log import logger
from agno.agent import Agent
from agno.models.openai import OpenAIChat

class FlightToolkit(Toolkit):
    def __init__(self, client_id: str, client_secret: str, debug: bool = False):
        """
        Initialize the Flight Toolkit with Amadeus API credentials.
        
        Args:
            client_id (str): Amadeus API client ID
            client_secret (str): Amadeus API client secret
            debug (bool): Enable debug mode for detailed logging
        """
        super().__init__(name="flight_tools")
        self.client_id = client_id
        self.client_secret = client_secret
        self.debug = debug
        self.amadeus = Client(
            client_id=client_id,
            client_secret=client_secret,
            logger=logger if debug else None,
            log_level='debug' if debug else 'warning',
            hostname='test'
        )
        self.register(self.search_flights)
    
    def search_flights(self, 
                     origin: str, 
                     destination: str, 
                     departure_date: str, 
                     return_date: Optional[str] = None, 
                     adults: int = 1, 
                     currency: str = 'INR', 
                     max_results: int = 5, 
                     non_stop: bool = False, 
                     travel_class: Optional[str] = None) -> str:
        """
        Search for flights using Amadeus Flight Offers Search API.
        
        Args:
            origin (str): IATA code of origin airport (3 letters)
            destination (str): IATA code of destination airport (3 letters)
            departure_date (str): Departure date in YYYY-MM-DD format
            return_date (str, optional): Return date in YYYY-MM-DD format for round trips
            adults (int, optional): Number of adult passengers. Default is 1.
            currency (str, optional): Currency code. Default is 'USD'.
            max_results (int, optional): Maximum number of results. Default is 25.
            non_stop (bool, optional): Filter for non-stop flights only. Default is False.
            travel_class (str, optional): Travel class. Options: 'ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST'
            
        Returns:
            str: JSON string with flight results or error message
        """
        # Log environment info for debugging
        if self.debug:
            logger.info(f"Amadeus client configuration: {self.amadeus.host}")
        
        try:
            # Validate inputs
            self._validate_inputs(origin, destination, departure_date, return_date, adults)
            
            # Use tomorrow's date if no date is provided (for testing)
            if not departure_date:
                departure_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Prepare the API request
            kwargs = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": departure_date,
                "adults": adults,
                "currencyCode": currency,
                "max": max_results
            }
            
            # Add optional parameters if provided
            if return_date:
                kwargs["returnDate"] = return_date
            
            # Fix for nonStop parameter - use string representation instead of boolean
            if non_stop:
                kwargs["nonStop"] = "true"  # Use string instead of boolean
                
            if travel_class and travel_class in ['ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS', 'FIRST']:
                kwargs["travelClass"] = travel_class
            
            # Log request details in debug mode
            if self.debug:
                logger.info(f"Request parameters: {kwargs}")
            
            # Make API call
            response = self.amadeus.shopping.flight_offers_search.get(**kwargs)
            
            # Process the response and convert to JSON string
            processed_results = self._process_flight_results(response.data)
            return json.dumps(processed_results, indent=2)  # Convert dict to JSON string
        
        except ResponseError as error:
            error_details = self._parse_error_response(error)
            logger.error(f"API Error: {error_details}")
            # Return error as string instead of dict
            return f"Error searching flights: {error_details}"
        
        except ValueError as error:
            logger.error(f"Validation Error: {error}")
            # Return error as string instead of dict
            return f"Validation error: {str(error)}"
        
        except Exception as error:
            logger.error(f"Unexpected Error: {error}", exc_info=True)
            # Return error as string instead of dict
            return f"An unexpected error occurred: {str(error)}"
    
    def _validate_inputs(self, origin, destination, departure_date, return_date, adults):
        """Validate input parameters"""
        
        # Check airport codes
        if not origin or not destination:
            raise ValueError("Origin and destination airport codes are required")
        
        if len(origin) != 3 or len(destination) != 3:
            raise ValueError("Airport codes must be 3-letter IATA codes")
        
        # Validate date format
        if departure_date:
            try:
                departure_dt = datetime.strptime(departure_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Departure date must be in YYYY-MM-DD format")
        
        if return_date:
            try:
                return_dt = datetime.strptime(return_date, '%Y-%m-%d')
                
                # Check if return date is after departure date
                if departure_date and return_dt < datetime.strptime(departure_date, '%Y-%m-%d'):
                    raise ValueError("Return date must be after departure date")
            except ValueError as e:
                if "must be after" in str(e):
                    raise e
                else:
                    raise ValueError("Return date must be in YYYY-MM-DD format")
        
        # Validate adults
        if not isinstance(adults, int) or adults < 1:
            raise ValueError("Number of adults must be a positive integer")
    
    def _parse_error_response(self, error):
        """Extract detailed error information from Amadeus error response"""
        try:
            if hasattr(error, 'response'):
                if hasattr(error.response, 'body') and error.response.body:
                    error_body = json.loads(error.response.body)
                    if 'errors' in error_body and error_body['errors']:
                        error_details = []
                        for err in error_body['errors']:
                            detail = f"{err.get('title', 'Error')}: {err.get('detail', 'Unknown error')}"
                            if 'source' in err and 'parameter' in err['source']:
                                detail += f" (parameter: {err['source']['parameter']})"
                            error_details.append(detail)
                        return "; ".join(error_details)
            return str(error)
        except Exception:
            return str(error)
    
    def _process_flight_results(self, flight_data):
        """
        Process and simplify flight search results.
        
        Args:
            flight_data (list): Raw flight data from Amadeus API
            
        Returns:
            dict: Simplified flight data
        """
        if not flight_data:
            return {"count": 0, "flights": []}
        
        processed_results = {
            "count": len(flight_data),
            "flights": []
        }
        
        for offer in flight_data:
            flight_details = {
                "id": offer['id'],
                "price": {
                    "total": offer['price']['total'],
                    "currency": offer['price']['currency']
                },
                "itineraries": []
            }
            
            for itinerary in offer['itineraries']:
                segments = []
                
                for segment in itinerary['segments']:
                    segments.append({
                        "departure": {
                            "iataCode": segment['departure']['iataCode'],
                            "terminal": segment['departure'].get('terminal', 'N/A'),
                            "at": segment['departure']['at']
                        },
                        "arrival": {
                            "iataCode": segment['arrival']['iataCode'],
                            "terminal": segment['arrival'].get('terminal', 'N/A'),
                            "at": segment['arrival']['at']
                        },
                        "carrierCode": segment['carrierCode'],
                        "flightNumber": segment['number'],
                        "aircraft": segment.get('aircraft', {}).get('code', 'N/A'),
                        "duration": segment.get('duration', 'N/A')
                    })
                
                flight_details["itineraries"].append({
                    "duration": itinerary.get('duration', 'N/A'),
                    "segments": segments
                })
            
            processed_results["flights"].append(flight_details)
        
        return processed_results



client_id = "3k11YFnI3vrwERi7fPXgAvFjQexfY7gg"
client_secret = "6r9LW52D17vr6UWx"

# Create the toolkit
flight_toolkit = FlightToolkit(client_id=client_id, client_secret=client_secret, debug=True)

def main():
    # Create an agent with the flight toolkit
    agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),  # or other model of your choice
        markdown=True,
        tools=[flight_toolkit],
        show_tool_calls=True,
        add_datetime_to_instructions=True,
        instructions=['Use the flight toolkit to find flights',
        'Use Current date and time which are passed with the instructions']
    )
    
    # Example query
    agent.print_response("Find flights from JFK to LHR on 2025-03-15")


if __name__ == "__main__":
    main()
