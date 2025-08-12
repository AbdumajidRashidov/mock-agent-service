# Truck Updater Service

A FastAPI-based service for retrieving and processing truck location data, calculating journey progress, and notifying brokers about truck status updates.

## Features

-   Retrieve truck location data from external API
-   Calculate journey progress based on origin, destination, and current location
-   Send notifications to brokers about truck status
-   Health check endpoint

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Start the service:

```bash
python main.py
```

The service will be available at http://localhost:8000

## API Endpoints

### Get Truck Location

```
GET /trucks/location?truck_id={truck_id}&project_name={project_name}
```

Retrieves the current location of a truck from the external API.

### Calculate Journey Progress

```
POST /trucks/journey-progress?truck_id={truck_id}&project_name={project_name}
```

Calculates the journey progress of a truck based on origin, destination, and current location.

Request body:

```json
{
    "origin": {
        "lat": 40.7128,
        "lng": -74.006
    },
    "destination": {
        "lat": 34.0522,
        "lng": -118.2437
    },
    "current_location": {
        "lat": 39.7392,
        "lng": -86.1519
    }
}
```

### Notify Broker

```
POST /brokers/notify
```

Sends a notification to a broker about a truck's status.

Request body:

```json
{
    "broker_id": "broker123",
    "truck_id": "truck456",
    "message": "Truck is delayed due to traffic",
    "delay_minutes": 30,
    "new_eta": "2025-03-19T15:30:00"
}
```

### Health Check

```
GET /health
```

Verifies that the service is running properly.

## API Documentation

FastAPI automatically generates interactive API documentation:

-   Swagger UI: http://localhost:8000/docs
-   ReDoc: http://localhost:8000/redoc
