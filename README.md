# TourMoreAI - AI-Powered Travel Planning System

TourMoreAI is an advanced travel planning assistant that leverages AI agents to create comprehensive travel itineraries. The system helps users plan their trips by analyzing travel requests, searching for flights, gathering destination information, and generating detailed travel plans.

## Features

- **Natural Language Trip Planning**: Simply describe your travel plans in natural language
- **Flight Search**: Searches and recommends flights using the Amadeus API
- **Destination Research**: Provides information about accommodations, dining, attractions, and transportation
- **Navigation Assistance**: Offers directions and transportation options between locations
- **Complete Itinerary Generation**: Creates day-by-day travel plans with all details combined

## Architecture

TourMoreAI uses a multi-agent workflow built on the Agno framework:

1. **Travel Information Extractor**: Parses user requests for key travel details
2. **Flight Search Agent**: Finds and recommends flights via Amadeus API
3. **Destination Information Agent**: Researches accommodation, dining, and attractions
4. **Navigation Agent**: Provides directions between locations using Google Maps
5. **Travel Plan Generator**: Compiles all information into a complete itinerary

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Gokul712003/TourMoreAI.git
cd TourMoreAI
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

3. Set up environment variables in a `.env` file:
```
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
OPENAI_API_KEY=your_openai_api_key
```

4. Update the Amadeus API credentials in `TourMoreAI.py` (or move to environment variables):
```python
client_id = "your_amadeus_client_id"
client_secret = "your_amadeus_client_secret"
```

## Usage

Run the application:
```bash
python TourMoreAI.py
```

This starts a web interface (Playground) where you can interact with the travel planning system. Enter your travel request in natural language, for example:

```
I'd like to plan a trip to Paris for 5 days in June 2025. I'm interested in art museums and fine dining, 
with mid-range budget accommodations. I'll be traveling for tourism purposes.
```

The system will:
1. Extract your travel details
2. Search for flights
3. Find accommodations, restaurants, and attractions
4. Generate a complete day-by-day itinerary

## API Keys

This project requires the following API keys:

1. **Amadeus API**: For flight search functionality
   - Register at [Amadeus for Developers](https://developers.amadeus.com/)
   - Create a new app to get client ID and secret
   - Update in the code or add to environment variables

2. **Google Maps API**: For location search and navigation
   - Get an API key from [Google Cloud Platform](https://console.cloud.google.com/)
   - Enable Maps JavaScript API, Places API, and Directions API
   - Add to your `.env` file as `GOOGLE_MAPS_API_KEY`

3. **OpenAI API**: For the AI agents
   - Get an API key from [OpenAI](https://platform.openai.com/)
   - Add to your `.env` file as `OPENAI_API_KEY`

## Components

- `TourMoreAI.py`: Main workflow orchestrator
- `flight_toolkit.py`: Flight search tools using Amadeus API
- `simplified_map_tools.py`: Simplified Google Maps integration

## Example

Input:
```
I want to visit New York City for a week in April 2025. I'm interested in Broadway shows and 
sightseeing. I prefer luxury hotels and need recommendations for fine dining. I'll be traveling for leisure.
```

Output will include:
- Extracted trip details (destination, dates, preferences)
- Flight options with prices and schedules
- Hotel recommendations matching preferences
- Restaurant and attraction suggestions
- A day-by-day itinerary with all details combined

## Limitations

- Flight search requires valid IATA airport codes
- All API keys must be valid and have sufficient quota
- Some functionality may be limited based on API restrictions
- The application requires internet connectivity
