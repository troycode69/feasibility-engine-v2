import vertexai
from google import genai
from google.cloud import aiplatform

# AUTHENTICATION: Ensure local credentials exist via:
# gcloud auth application-default login [1]

PROJECT_ID = "your-project-id"
LOCATION = "us-central1"

# Initialize the higher-level Vertex AI SDK [2, 3]
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Initialize the Gen AI SDK Client specifically for Vertex AI backend [4]
# BEST PRACTICE: Use client-level scoping for multi-project/location applications 
# to improve discoverability and cohesiveness [5].
client = genai.Client(
    vertexai=True, 
    project=PROJECT_ID, 
    location=LOCATION
)
2. Retrieval (RAG)
The following pattern demonstrates how to ground the Gemini model using a knowledge base or search tool to retrieve information like storage unit manuals or prices.
from google.genai.types import GenerateContentConfig, Tool, GroundingChunk

# BEST PRACTICE: Use 'Streaming' for responses to reduce perceived latency.
# Streaming allows you to act on chunks early (e.g., query classification) [6, 7].

def query_storage_knowledge_base(user_query: str):
    # Pattern to ground responses using RAG [8, 9]
    # This example uses a Tool approach to fetch from a search index
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_query,
        config=GenerateContentConfig(
            # Grounding with Vertex AI Search allows retrieving 
            # up-to-date data from specific knowledge bases [8, 9].
            tools=[Tool(google_search_retrieval={})] 
        )
    )
    return response.text

# COST OPTIMIZATION: Aim to provide only relevant tools for the task. 
# Providing too many tools (recommended max 10-20) increases the risk 
# of suboptimal tool selection and increases character counts [10, 11].
3. Function Calling: "Book a Unit"
This pattern defines a specific tool that the AI triggers when it detects the intent to finalize a booking in your database.
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerativeModel,
    Tool,
    GenerationConfig
)

# 1. Define the Python function for the logic
def book_storage_unit(unit_id: str, customer_id: str, start_date: str):
    """
    Books a specific storage unit for a customer.
    Args:
        unit_id: The unique identifier for the storage unit (e.g., '10x10-CC-01').
        customer_id: The unique identifier for the customer.
        start_date: The requested move-in date.
    """
    # Database logic to update 'status' to 'booked' would go here.
    return {"status": "success", "booking_id": "BK-999"}

# 2. Declare the function as a tool [2, 12]
# BEST PRACTICE: Use clear and detailed names/descriptions.
# The model relies on these descriptions to choose the correct tool [13].
booking_tool = Tool(
    function_declarations=[
        FunctionDeclaration.from_func(book_storage_unit)
    ]
)
# 3. Initialize model with the tool
model = GenerativeModel("gemini-2.5-flash")

# ANTI-PATTERN: Avoid high temperature for function calling.
# BEST PRACTICE: Use temperature 0 (or very low) to ensure confident results 
# and reduce hallucinations [2, 14].
response = model.generate_content(
    "I'd like to book unit 10x10-CC-01 for customer 555 starting tomorrow.",
    tools=[booking_tool],
    generation_config=GenerationConfig(temperature=0)
)

# LATENCY NOTE: For Gemini 3 and later, you can stream function call arguments 
# as they are generated to further reduce latency [7, 15].
