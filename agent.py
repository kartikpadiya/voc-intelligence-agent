import json
import os
from groq import Groq
from dotenv import load_dotenv
from database import init_database, get_stats
from parser import parse_and_load
from analyzer import analyze_all_reviews, analyze_weekly_reviews, answer_question, get_theme_summary
from reporter import generate_global_report, generate_weekly_report
from pdf_generator import generate_pdf

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_database_stats",
            "description": "Get current database statistics - total reviews, by product, by sentiment.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_reviews",
            "description": "Run AI sentiment analysis and theme tagging on all unanalyzed reviews.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_global_report",
            "description": "Generate comprehensive global action items report segmented by department.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_weekly_report",
            "description": "Generate weekly delta report based on new reviews this week.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_pdf_report",
            "description": "Generate a beautiful PDF report with charts and AI insights.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_theme_analysis_for_product",
            "description": "Get theme analysis summary for a product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "master_buds_1 or master_buds_max"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "answer_customer_question",
            "description": "Answer any analytical question about reviews grounded in database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to answer about the reviews."
                    }
                },
                "required": ["question"]
            }
        }
    }
]


def execute_tool(tool_name, tool_args):
    print(f"\n[AGENT CALLING TOOL]: {tool_name}")

    if tool_name == "get_database_stats":
        stats = get_stats()
        return json.dumps(stats)

    elif tool_name == "analyze_reviews":
        analyze_all_reviews()
        return "Analysis complete."

    elif tool_name == "generate_global_report":
        result = generate_global_report()
        return "Global report saved to reports/ folder."

    elif tool_name == "generate_weekly_report":
        result = generate_weekly_report()
        return "Weekly report saved to reports/ folder."

    elif tool_name == "generate_pdf_report":
        result = generate_pdf()
        return f"PDF saved: {result}"

    elif tool_name == "get_theme_analysis":
        product_id = tool_args.get("product_id", None)
        summary = get_theme_summary(product_id)
        return json.dumps(summary)

    elif tool_name == "answer_customer_question":
        question = tool_args.get("question", "")
        answer = answer_question(question)
        return answer

    else:
        return f"Unknown tool: {tool_name}"


def run_agent(user_message, max_iterations=10):
    print("\n" + "="*50)
    print(f"YOU: {user_message}")
    print("="*50)

    system_prompt = """You are VocBot, an autonomous Voice of Customer Intelligence Agent.
You analyze customer reviews for audio products.
You have tools to analyze data, generate reports, and answer questions.
When given a task, use tools to complete it step by step.
Be autonomous and thorough."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    for iteration in range(max_iterations):
        print(f"\n[AGENT THINKING - Step {iteration+1}]")

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=1000
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in (message.tool_calls or [])
            ] if message.tool_calls else []
        })

        if finish_reason == "stop" or not message.tool_calls:
            print("\n" + "="*50)
            print("VOCBOT ANSWER:")
            print("="*50)
            print(message.content)
            return message.content

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except:
                tool_args = {}

            tool_result = execute_tool(tool_name, tool_args)
            print(f"[TOOL RESULT]: {str(tool_result)[:150]}...")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_result)
            })

    return "Max iterations reached."


def interactive_mode():
    print("="*50)
    print("VocBot - Voice of Customer Agent")
    print("Type 'exit' to quit")
    print("="*50)
    print("\nTry asking:")
    print("  - What are top complaints about Master Buds 1?")
    print("  - Compare both products on sound quality")
    print("  - Generate reports")
    print("  - Generate PDF report")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        if not user_input:
            continue

        run_agent(user_input)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run_agent(" ".join(sys.argv[1:]))
    else:
        interactive_mode()
