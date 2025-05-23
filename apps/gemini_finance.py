from google import genai
from google.genai import types
from config import Config
import pandas as pd
import yfinance as yf

def gemini_finance_response(prompt):
    # Define the function declaration for the model
    get_financial_info_function = {
        "name": "get_financial_info",
        "description": "Retrieve financial data such as income statements, balance sheets and cashflow using the ticker symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Ticker symbol of a company (e.g., 'NVDA' for NVIDIA company)",
                },
            },
            "required": ["ticker"],
        },
    }

    def get_financial_info(ticker):
        t = yf.Ticker(ticker)
        income_stmt = t.financials
        balance_sheet = t.balance_sheet
        cash_flow = t.cashflow
        
        # Format the data with proper headers and index
        return {
            'income_statement': income_stmt.to_string(),
            'balance_sheet': balance_sheet.to_string(),
            'cash_flow': cash_flow.to_string()
        }

    # Configure the client and tools
    client = genai.Client(api_key=Config.GEMINI_API_KEY)
    finance_tools = [
        types.Tool(function_declarations=[get_financial_info_function])
    ]
    config = {
        "tools": finance_tools,
        "automatic_function_calling": {"disable": True},
        # Force the model to call 'any' function, instead of chatting.
        "tool_config": {"function_calling_config": {"mode": "any"}},
    }

    # Send request with function declarations
    contents = [
        types.Content(
            role="user", parts=[types.Part(text="Provide financial insights for the company GlobalFoundries")]
        )
    ]
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=config,
    )

    print(response.candidates[0].content.parts[0].function_call)

    # Extract tool call details
    tool_call = response.candidates[0].content.parts[0].function_call

    if tool_call.name == "get_financial_info":
        result = get_financial_info(**tool_call.args)
        print(f"Function execution result: ok")

    # Create a function response part
    function_response_part = types.Part.from_function_response(
        name=tool_call.name,
        response={"result": result},
    )

    # Append function call and result of the function execution to contents
    contents.append(types.Content(role="model", parts=[types.Part(function_call=tool_call)])) # Append the model's function call message
    contents.append(types.Content(role="user", parts=[function_response_part])) # Append the function response


    final_response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
    )

    return final_response.text
