import FunctionDeclaration, Tool

# BEST PRACTICE: Use clear and detailed names/descriptions to ensure 
# the model selects the correct tool [5].
check_unit_availability_func = FunctionDeclaration(
    name="check_unit_availability",
    description="Check real-time availability for storage units. Use this tool when a user asks about renting a specific size unit, wants to know if a unit is available at a specific location, or provides a move-in date.",
    parameters={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city, state, or geographic area of the storage facility."
            },
            "unit_size": {
                "type": "string",
                "description": "The dimensions of the storage unit (e.g., '10x10', '5x5') or type (e.g., 'climate controlled')."
            },
            "date": {
                "type": "string",
                "description": "The requested move-in date in ISO 8601 format (e.g., '2026-05-20')."
            }
        },
        "required": ["location", "unit_size", "date"]
    }
)

# This object is ready for the tools=[...] parameter [1, 6]
storage_tools = Tool(
    function_declarations=[check_unit_availability_func]
)
2. Define the Action: execute_check_availability
This function simulates the backend database call, querying for units that match the platform’s Product Catalog Schema (e.g., size, price, and status).
def execute_check_availability(location: str, unit_size: str, date: str):
    """
    Simulates a database query for storage unit availability.
    """
    # Logic here would query the Firestore or Retail API inventory [7, 8]
    # For this example, we return a mock response matching our data model.
    return {
        "status": "success",
        "location": location,
        "date_queried": date,
        "units": [
            {
                "id": "unit_99b",
                "title": f"{unit_size} Climate Controlled Unit",
                "price": 150.00,
                "availability": "IN_STOCK"
            }
        ]
    }
3. Define the Hand-off: Response Parsing Logic
This snippet demonstrates how to parse the function_call from Gemini's response, execute the Python code, and send the results back to the model for a final natural language answer.
from vertexai.generative_models import GenerativeModel, Content, Part, GenerationConfig

model = GenerativeModel("gemini-2.5-flash")

# BEST PRACTICE: Set temperature to 0 for deterministic function calling [10].
chat = model.start_chat()
user_prompt = "I need a 10x10 in Austin for next Friday."

# Turn 1: Get the function call suggestion from the model
response = chat.send_message(
    user_prompt, 
    tools=[storage_tools],
    generation_config=GenerationConfig(temperature=0)
)

# Hand-off logic: Extract and execute
function_call = response.candidates.function_calls

if function_call.name == "check_unit_availability":
    # Extract arguments dynamically from the model's structured output [11]
    api_response = execute_check_availability(
        location=function_call.args["location"],
        unit_size=function_call.args["unit_size"],
        date=function_call.args["date"]
    )

    # Turn 2: Provide the API output back to the model for the final response [2, 12]
    final_response = chat.send_message(
        Part.from_function_response(
            name="check_unit_availability",
            response={"content": api_response}
        )
    )

    print(final_response.text)