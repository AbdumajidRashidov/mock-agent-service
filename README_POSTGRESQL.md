# PostgreSQL Database Integration

This document provides instructions for setting up and using the PostgreSQL database integration for the agents service.

## Database Setup

### Prerequisites

-   PostgreSQL 12 or higher
-   Python 3.8 or higher
-   psycopg2-binary package

### Environment Variables

The following environment variables are used for database configuration:

```
# PostgreSQL Database Configuration
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=numeo_agents
```

These can be set in your `.env` file or directly in your environment.

## Database Schema

The following tables will be created:

### 1. load_replies

Stores information about load replies.

```sql
CREATE TABLE IF NOT EXISTS load_replies (
    id UUID PRIMARY KEY,
    carrier_id VARCHAR(255),
    load_id VARCHAR(255),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

### 2. warnings

Stores warnings related to load replies.

```sql
CREATE TABLE IF NOT EXISTS warnings (
    id UUID PRIMARY KEY,
    load_reply_id UUID REFERENCES load_replies(id),
    warning_type VARCHAR(50),
    description TEXT,
    severity VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

### 3. rates

Stores rate information associated with load replies.

```sql
CREATE TABLE IF NOT EXISTS rates (
    id UUID PRIMARY KEY,
    load_reply_id UUID REFERENCES load_replies(id),
    rate_per_mile DECIMAL(10, 2),
    total_rate DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

### 4. load_details

Stores details related to loads.

```sql
CREATE TABLE IF NOT EXISTS load_details (
    id UUID PRIMARY KEY,
    load_reply_id UUID REFERENCES load_replies(id),
    origin VARCHAR(255),
    destination VARCHAR(255),
    distance DECIMAL(10, 2),
    weight DECIMAL(10, 2),
    dimensions VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

### 5. conversation_history

Stores conversation history for tracking interactions.

```sql
CREATE TABLE IF NOT EXISTS conversation_history (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255),
    agent_type VARCHAR(50),
    role VARCHAR(50),
    content TEXT,
    thread_id VARCHAR(255),
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

## Implementation Plan

To implement PostgreSQL integration in your agent system:

1. **Install Required Packages**

    ```bash
    pip install psycopg2-binary python-dotenv
    ```

2. **Create Database Connection Module**
   Create a new file `src/db/connection.py` with functions for:

    - Establishing database connections
    - Executing SQL queries
    - Creating database tables

3. **Create Database Operations Module**
   Create a new file `src/db/operations.py` with classes for:

    - CRUD operations for each table
    - Data validation and formatting

4. **Create Conversation History Utilities**
   Create utilities for:

    - Saving messages to the database
    - Retrieving conversation history
    - Formatting conversations for LLMs

5. **Update Agent Implementations**
   Update your agent files to:
    - Save conversation history to the database
    - Retrieve conversation history for context
    - Store agent-specific data (warnings, rates, etc.)

## Docker Setup (Optional)

If you prefer to use Docker for PostgreSQL, you can use the following Docker Compose configuration:

```yaml
version: '3.8'

services:
    postgres:
        image: postgres:16
        environment:
            POSTGRES_USER: postgres
            POSTGRES_PASSWORD: postgres
            POSTGRES_DB: numeo_agents
        ports:
            - '5432:5432'
        volumes:
            - postgres_data:/var/lib/postgresql/data

volumes:
    postgres_data:
```

Save this to a `docker-compose.yml` file and run:

```bash
docker compose up -d postgres
```
