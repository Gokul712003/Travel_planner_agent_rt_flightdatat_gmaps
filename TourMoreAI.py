import json
from typing import Iterator, Optional, List
import os
from flight_toolkit import FlightToolkit
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.workflow.sqlite import SqliteWorkflowStorage
from agno.tools.google_maps import GoogleMapTools
from agno.tools.googlesearch import GoogleSearchTools
from agno.utils.log import logger
from agno.utils.pprint import pprint_run_response
from agno.workflow import RunEvent, RunResponse, Workflow
from agno.playground import Playground, serve_playground_app
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from dotenv import load_dotenv  
from simplified_map_tools import SimplifiedMapTools
load_dotenv()

# Initialize flight toolkit
client_id = "3k11YFnI3vrwERi7fPXgAvFjQexfY7gg"
client_secret = "6r9LW52D17vr6UWx"
flight_toolkit = FlightToolkit(client_id=client_id, client_secret=client_secret, debug=True)

# Define response models for structured outputs
class FlightDetails(BaseModel):
    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_date: str = Field(..., description="Departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(None, description="Return date in YYYY-MM-DD format (optional)")
    recommended_flights: str = Field(..., description="Summary of recommended flight options with times and prices")
    best_option: str = Field(..., description="The single best flight option with details")

class DestinationInfo(BaseModel):
    accommodations: str = Field(..., description="Top hotels or accommodations with ratings and price ranges")
    dining: str = Field(..., description="Notable restaurants and eateries with cuisine types and ratings")
    attractions: str = Field(..., description="Key tourist attractions with brief descriptions")
    transportation: str = Field(..., description="Local transportation options like bus stops, metro stations, airports")
    urls: Optional[List[str]] = Field(None, description="URLs for more information about the destination")
    
class TravelInfo(BaseModel):
    destination: str = Field(..., description="Main destination city or location")
    duration: str = Field(..., description="Length of stay")
    travel_dates: str = Field(..., description="Travel dates")
    purpose: str = Field(..., description="Purpose of travel (tourism, business, etc.)")
    preferences: str = Field(..., description="Traveler preferences (budget, luxury, adventure, etc.)")
    special_requests: Optional[str] = Field(None, description="Any special requests or considerations")

class TravelPlannerWorkflow(Workflow):
    # Agent 1: Travel Information Extractor
    travel_info_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions=[
            "You are a travel planning assistant that extracts key information from a user's travel plan or request.",
            "Extract details about the desired destination, travel dates, duration, purpose, and preferences.",
            "Ask clarifying questions if any essential information is missing.",
            "Format the response as structured information about the travel plan."
        ],
        add_history_to_messages=True,
        add_datetime_to_instructions=True,
        response_model=TravelInfo,
        structured_outputs=True,
        debug_mode=False,
    )
    
    # Agent 2: Flight Search Agent
    flight_search_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[flight_toolkit],
        instructions=[
            "You are a flight booking assistant that helps users find the best flights for their trip.",
            "Use the flight toolkit to search for flights based on the user's travel information.",
            "The flight search results will be returned as a JSON string. Parse this JSON to extract flight details.",
            "Summarize the flight options clearly with departure/arrival times and prices.",
            "Recommend the best option based on price, duration, and convenience.",
            "Current date and time are passed with the instructions.",
            "For flight searches, only use future dates (at least tomorrow or later).",
            f"Today's date is {datetime.now().strftime('%Y-%m-%d')}"
        ],
        add_history_to_messages=True,
        add_datetime_to_instructions=True,
        response_model=FlightDetails,
        structured_outputs=True,
        show_tool_calls=True,
        debug_mode=False,
    )
    
    # Agent 3: Destination Information Agent
    destination_info_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[SimplifiedMapTools(), GoogleSearchTools()],  # Use simplified tools instead
        instructions=[
            "You are a destination guide that provides comprehensive information about travel destinations.",
            "Use the tools to find hotels, eating spots, tourist attractions, and transportation options.",
            "For each category, provide at least 3-5 recommendations with ratings, location details, and other relevant information.",
            "Focus on options that match the traveler's preferences (budget, luxury, adventure, etc.).",
            "Format the information clearly and concisely for easy reading.",
            "Do not attempt to get directions between places, only search for locations."
        ],
        add_history_to_messages=True,
        add_datetime_to_instructions=True,
        response_model=DestinationInfo,
        structured_outputs=True,
        show_tool_calls=True,
        debug_mode=False,
    )
    
    # Agent 4: Navigation Agent
    navigation_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o-mini"),
        tools=[GoogleMapTools()],
        instructions=[
            "You are a navigation assistant that helps travelers get from one place to another.",
            "Use Google Maps to show directions between locations when asked by the user.",
            "Provide step-by-step directions with transportation options (walking, public transit, driving, etc.).",
            "Include estimated travel times and distances.",
            "Format directions in a clear, easy-to-follow manner."
        ],
        add_history_to_messages=True,
        markdown=True,
        show_tool_calls=True,
        debug_mode=False,
    )
    
    # Agent 5: Travel Plan Generator
    travel_plan_agent: Agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions=[
            "You are a travel plan generator that creates comprehensive itineraries.",
            "Using all the provided information about flights, accommodations, attractions, and transportation,",
            "Create a day-by-day itinerary that includes flight details, where to stay, what to see/do, and where to eat.",
            "Make the plan realistic in terms of timing and distances.",
            "Format the plan as a well-structured travel itinerary with headings and sections.",
            "Include practical tips specific to the destination."
        ],
        add_history_to_messages=True,
        markdown=True,
        debug_mode=False,
    )

    def extract_travel_info(self, travel_request: str) -> Optional[TravelInfo]:
        """Extract essential travel information from the user's request"""
        try:
            response: RunResponse = self.travel_info_agent.run(travel_request)
            
            if not response or not response.content:
                logger.warning("Empty Travel Information response")
            if not isinstance(response.content, TravelInfo):
                logger.warning("Invalid response type for Travel Information")
                
            return response.content
            
        except Exception as e:
            logger.warning(f"Failed to extract travel info: {str(e)}")
            
        return None
    
    def search_flights(self, travel_info: TravelInfo) -> Optional[FlightDetails]:
        """Search for flights based on travel information"""
        try:
            # Format the input for flight search
            flight_search_query = (
                f"I need flights to {travel_info.destination}. "
                f"Departing around {travel_info.travel_dates}. "
                f"My trip is for {travel_info.duration}. "
                f"Preferences: {travel_info.preferences}. "
                f"Purpose: {travel_info.purpose}. "
            )
            
            response: RunResponse = self.flight_search_agent.run(flight_search_query)
            
            if not response or not response.content:
                logger.warning("Empty Flight Search response")
            if not isinstance(response.content, FlightDetails):
                logger.warning("Invalid response type for Flight Search")
                
            return response.content
            
        except Exception as e:
            logger.warning(f"Failed to search flights: {str(e)}")
            
        return None
    
    def get_destination_info(self, travel_info: TravelInfo) -> Optional[DestinationInfo]:
        """Get detailed information about the destination"""
        try:
            # Format the query for destination info
            destination_query = (
                f"I'm traveling to {travel_info.destination} for {travel_info.duration}. "
                f"Please find me good {travel_info.preferences} accommodations, "
                f"restaurants, tourist attractions, and public transportation options near city center. "
                f"Purpose of visit: {travel_info.purpose}. "
            )
            
            response: RunResponse = self.destination_info_agent.run(destination_query)
            
            if not response or not response.content:
                logger.warning("Empty Destination Information response")
            if not isinstance(response.content, DestinationInfo):
                logger.warning("Invalid response type for Destination Information")
                
            return response.content
            
        except Exception as e:
            logger.warning(f"Failed to get destination info: {str(e)}")
            
            # Provide fallback information if the normal method fails
            fallback_info = DestinationInfo(
                accommodations="Could not retrieve accommodations due to an error. Please search for hotels in your destination area.",
                dining="Could not retrieve dining information due to an error. Please search for restaurants in your destination area.",
                attractions="Could not retrieve attractions due to an error. Please search for tourist spots in your destination area.",
                transportation="Could not retrieve transportation options."
            )
            
            return fallback_info
    
    def get_navigation_info(self, origin: str, destination: str) -> Optional[str]:
        """Get navigation directions between two points"""
        try:
            navigation_query = f"How do I get from {origin} to {destination}? Please show me the directions."
            
            response: RunResponse = self.navigation_agent.run(navigation_query)
            
            if not response or not response.content:
                logger.warning("Empty Navigation response")
                
            return response.content
            
        except Exception as e:
            logger.warning(f"Failed to get navigation info: {str(e)}")
            
        return None
    
    def generate_travel_plan(self, travel_info: TravelInfo, flight_details: FlightDetails, 
                            destination_info: DestinationInfo) -> Optional[str]:
        """Generate a comprehensive travel plan using all gathered information"""
        try:
            # Compile all information for the travel plan generator
            travel_plan_input = {
                "travel_info": travel_info.model_dump(),
                "flight_details": flight_details.model_dump(),
                "destination_info": destination_info.model_dump()
            }
            
            response: RunResponse = self.travel_plan_agent.run(json.dumps(travel_plan_input, indent=4))
            
            if not response or not response.content:
                logger.warning("Empty Travel Plan response")
                
            return response.content
            
        except Exception as e:
            logger.warning(f"Failed to generate travel plan: {str(e)}")
            
        return None
    
    def run(self, travel_request: str) -> Iterator[RunResponse]:
        """Run the complete travel planning workflow"""
        logger.info(f"Generating a travel plan for: {travel_request}")
        
        # Step 1: Extract travel information
        yield RunResponse(content="Extracting travel details...")
        travel_info: Optional[TravelInfo] = self.extract_travel_info(travel_request)
        
        if travel_info is None:
            yield RunResponse(
                event=RunEvent.workflow_completed,
                content="Sorry, I couldn't extract the necessary travel information. Please provide more details about your trip."
            )
            return
        
        # Step 2: Search for flights
        yield RunResponse(content="Searching for flights...")
        flight_details: Optional[FlightDetails] = self.search_flights(travel_info)
        
        if flight_details is None:
            yield RunResponse(
                event=RunEvent.workflow_completed,
                content="Could not find suitable flights for your travel dates. Please try different dates or destinations."
            )
            return
        
        # Step 3: Get destination information
        yield RunResponse(content="Finding accommodation, dining, and attractions...")
        destination_info: Optional[DestinationInfo] = self.get_destination_info(travel_info)
        
        if destination_info is None:
            yield RunResponse(
                event=RunEvent.workflow_completed,
                content="Could not find detailed information about your destination. Let's continue with what we have."
            )
            return
        
        # Step 4: Generate travel plan
        yield RunResponse(content="Generating your complete travel plan...")
        travel_plan: Optional[str] = self.generate_travel_plan(travel_info, flight_details, destination_info)
        
        if travel_plan is None:
            yield RunResponse(
                event=RunEvent.workflow_completed,
                content="Could not generate a complete travel plan. Here's what I found so far:\n\n" +
                        f"**Flight Options**: {flight_details.recommended_flights}\n\n" +
                        f"**Best Flight**: {flight_details.best_option}\n\n" +
                        f"**Accommodations**: {destination_info.accommodations}\n\n" +
                        f"**Dining Options**: {destination_info.dining}\n\n" +
                        f"**Attractions**: {destination_info.attractions}\n\n" +
                        f"**Local Transportation**: {destination_info.transportation}"
            )
            return
        
        # Return the complete travel plan
        yield RunResponse(content=travel_plan, event=RunEvent.workflow_completed)

# Create the workflow instance
tour_more_ai_workflow = TravelPlannerWorkflow(
    name="TourMoreAI Travel Planner",
    workflow_id=f"tour-more-ai-planner",
    description="Complete travel planning workflow with flights, accommodations, and itinerary",
    storage=SqliteWorkflowStorage(
        table_name="tour_more_ai_workflow",
        db_file="tmp/agno_workflows.db",
    ),
)

# Create and serve the playground app
app = Playground(workflows=[tour_more_ai_workflow]).get_app()

if __name__ == "__main__":
    serve_playground_app(f"{os.path.splitext(os.path.basename(__file__))[0]}:app", reload=True)
