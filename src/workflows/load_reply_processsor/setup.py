# Creation of Azure client
import os
from openai import AsyncOpenAI

azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
openai_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-07-01-preview")

# Create the OpenAI client for Azure
azure_client = AsyncOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=f"{azure_endpoint}/openai/deployments/{openai_deployment_name}",
    default_headers={"api-key": os.getenv("AZURE_OPENAI_API_KEY")},
    default_query={"api-version": api_version},
)
