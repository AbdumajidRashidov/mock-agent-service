#!/usr/bin/env python3
"""
Centralized MongoDB connection module.
Provides a single connection pool for the entire application.
"""
import logging
import os
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

# Configure logger
logger = logging.getLogger(__name__)

# MongoDB client singleton
_mongo_client: Optional[MongoClient] = None
_db: Optional[Database] = None

def get_mongo_client() -> Optional[MongoClient]:
    """
    Get MongoDB client singleton with connection pooling.
    Returns None if connection fails.
    """
    global _mongo_client

    if _mongo_client is not None:
        return _mongo_client

    try:
        # Initialize MongoDB client with connection pooling and timeouts
        client = MongoClient(
            MONGODB_URI,
            maxPoolSize=50,
            readPreference='secondaryPreferred',
            serverSelectionTimeoutMS=5000,  # 5 second timeout for server selection
            connectTimeoutMS=10000,         # 10 second timeout for connection
            socketTimeoutMS=30000,          # 30 second timeout for socket operations
            retryWrites=True,
            retryReads=True
        )

        # Test the connection
        client.admin.command('ismaster')

        _mongo_client = client
        logger.info("MongoDB connection established successfully")
        return _mongo_client

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {str(e)}")
        return None

def get_database(database_name: str = "projects") -> Optional[Database]:
    """
    Get MongoDB database.
    Returns None if connection fails.
    """
    global _db

    if _db is not None:
        return _db

    client = get_mongo_client()
    if client is None:
        return None

    _db = client[database_name]
    return _db

def get_collection(collection_name: str, database_name: str = "projects") -> Optional[Collection]:
    """
    Get MongoDB collection.
    Returns None if connection fails.
    """
    db = get_database(database_name)
    if db is None:
        return None

    return db[collection_name]

def find_one(collection_name: str, query: Dict[str, Any], database_name: str = "projects") -> Optional[Dict[str, Any]]:
    """
    Find a single document in a collection.
    Returns None if connection fails or document not found.
    """
    collection = get_collection(collection_name, database_name)
    if collection is None:
        return None

    try:
        return collection.find_one(query)
    except Exception as e:
        logger.error(f"Error querying collection {collection_name}: {str(e)}")
        return None

def find_many(collection_name: str, query: Dict[str, Any], database_name: str = "projects", **kwargs):
    """
    Find multiple documents in a collection.
    Returns empty cursor if connection fails.

    Additional kwargs are passed to the find method (e.g., sort, limit, projection).
    """
    collection = get_collection(collection_name, database_name)
    if collection is None:
        return []

    try:
        return collection.find(query, **kwargs)
    except Exception as e:
        logger.error(f"Error querying collection {collection_name}: {str(e)}")
        return []

def update_one(collection_name: str, filter_query: Dict[str, Any], update_query: Dict[str, Any], 
               database_name: str = "projects", upsert: bool = False) -> bool:
    """
    Update a single document in a collection.
    Returns True if successful, False otherwise.
    
    Parameters:
    - collection_name: Name of the collection
    - filter_query: Query to find the document to update
    - update_query: Update operations to apply
    - database_name: Name of the database
    - upsert: If True, create a new document if no document matches the filter
    """
    collection = get_collection(collection_name, database_name)
    if collection is None:
        return False

    try:
        result = collection.update_one(filter_query, update_query, upsert=upsert)
        return result.acknowledged
    except Exception as e:
        logger.error(f"Error updating document in collection {collection_name}: {str(e)}")
        return False

# Initialize connection at module import time
get_mongo_client()
