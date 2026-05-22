# agent.py
import os
from dotenv import load_dotenv

load_dotenv()  # înainte de orice import care citește env vars

from google import genai
from google.genai import types
from prompts.registry import PromptRegistry
from tools.tool_wrapper import ToolWrapper
import tools.basic_tools  # noqa: F401 — înregistrează tool-urile în TOOL_REGISTRY

_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
_prompts = PromptRegistry(folder="prompts")
_tools = ToolWrapper()


def build_tools() -> list:
    """Converteste catalogul nostru in formatul cerut de google-genai."""
    catalog = _tools.catalog()
    declarations = []

    for tool in catalog:
        properties = {}
        for prop_name, prop_data in tool["input_schema"].get("properties", {}).items():
            properties[prop_name] = types.Schema(
                type=types.Type.STRING,
                description=prop_data.get("description", "")
            )

        declarations.append(
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=properties,
                    required=tool["input_schema"].get("required", [])
                )
            )
        )

    return [types.Tool(function_declarations=declarations)]


def execute_tool(name: str, args: dict) -> str:
    """Executa un tool si returneaza rezultatul ca string."""
    try:
        return str(_tools.call(name, args))
    except Exception as e:
        return f"Eroare la executia tool-ului '{name}': {str(e)}"


def react_loop(user_message: str, max_iterations: int = 10) -> str:
    """Loop ReAct: Think → Act → Observe → Repeat."""

    system_prompt = _prompts.render("planner")
    tools = build_tools()

    # Istoricul conversatiei
    contents = [types.Content(
        role="user",
        parts=[types.Part(text=user_message)]
    )]

    for iteration in range(max_iterations):

        # THINK: trimitem la Gemini
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tools,
            )
        )

        candidate = response.candidates[0].content

        # Adaugam raspunsul in istoric
        contents.append(candidate)

        # Verificam daca sunt tool calls
        tool_calls = [
            part.function_call
            for part in candidate.parts
            if part.function_call is not None
        ]

        # Daca nu sunt tool calls → raspuns final
        if not tool_calls:
            for part in candidate.parts:
                if part.text:
                    return part.text
            return "Agentul a terminat fara un raspuns text."

        # ACT + OBSERVE: executam tool-urile
        tool_results = []
        for tool_call in tool_calls:
            name = tool_call.name
            args = dict(tool_call.args)

            print(f"[Agent] Execut: {name} cu {args}")
            result = execute_tool(name, args)
            print(f"[Agent] Rezultat: {result[:100]}")

            tool_results.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=name,
                        response={"result": result}
                    )
                )
            )

        # Trimitem rezultatele inapoi
        contents.append(types.Content(role="user", parts=tool_results))

    return f"Eroare: agentul nu a putut finaliza in {max_iterations} iteratii."


def run():
    print("Agent Facturi pornit. Scrie 'exit' pentru a iesi.\n")

    while True:
        user_input = input("Tu: ").strip()

        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("La revedere!")
            break

        print("\nAgent: gandeste...\n")
        raspuns = react_loop(user_input)
        print(f"Agent: {raspuns}\n")
        print("-" * 50)


if __name__ == "__main__":
    run()