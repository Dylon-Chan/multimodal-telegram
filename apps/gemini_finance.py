from google import genai
from google.genai import types
from config import Config
import pandas as pd
import yfinance as yf

def gemini_finance_response(prompt):
    # Define the function declaration for the model
    get_financial_info_function = {
        "name": "get_financial_info",
        "description": "Retrieve annual financial statements including income statements, balance sheets, and cash flow statements from Yahoo Finance using a company's ticker symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol of a publicly traded company (e.g., 'NVDA' for NVIDIA, 'AAPL' for Apple Inc., 'MSFT' for Microsoft). Must be a valid ticker symbol listed on major stock exchanges.",
                },
            },
            "required": ["ticker"],
        },
    }

    def get_financial_info(ticker):
        t = yf.Ticker(ticker)
        
        # Get company info
        info = t.info
        company_name = info.get('longName', ticker)
        
        # Get financial statements
        income_stmt = t.financials
        balance_sheet = t.balance_sheet
        cash_flow = t.cashflow
        
        return {
            'company_name': company_name,
            'income_statement': income_stmt,
            'balance_sheet': balance_sheet,
            'cash_flow': cash_flow
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
            role="user", parts=[types.Part(text=prompt)]
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
        print(f"Financial data result: {result}")

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
