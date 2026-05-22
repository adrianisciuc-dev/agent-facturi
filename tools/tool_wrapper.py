# tools/tool_wrapper.py
from tools.registry import TOOL_REGISTRY


class ToolWrapper:
    """
    Interfața dintre agent și tool-uri.
    
    Analogie DE: ca un API layer între un dashboard și baza de date
    — dashboard-ul (agentul) nu accesează direct tabelele (tool-urile)
    ci trece prin API (ToolWrapper) care validează și execută.
    """

    @staticmethod
    def call(name: str, args: dict) -> str:
        """
        Execută un tool din TOOL_REGISTRY după nume și argumente.
        
        Analogie DE: ca un Airflow task executor
        — primește numele task-ului și parametrii, îl rulează și returnează rezultatul.
        
        Pași:
        1. Lookup  — caută tool-ul în TOOL_REGISTRY
        2. Validate — Pydantic verifică parametrii (din params_models.py)
        3. Execute  — rulează funcția efectivă (din basic_tools.py)
        4. Return   — returnează rezultatul către agent
        """

        # Pasul 1: Lookup — caută tool-ul în catalog
        # Analogie DE: ca un SELECT în metadata store
        # dacă tool-ul nu există → LLM a halucitat un nume inexistent
        if name not in TOOL_REGISTRY:
            return f"Eroare: tool '{name}' nu există în TOOL_REGISTRY."

        # Extragem tool-ul din catalog
        # tool conține: func, params_model, description
        tool = TOOL_REGISTRY[name]

        # Pasul 2: Validate — Pydantic verifică parametrii
        # Analogie DE: ca dbt tests înainte de a rula un model
        # params_model e clasa din params_models.py (ex: ReadInvoiceParams)
        # dacă args nu respectă schema → eroare clară înainte de execuție
        try:
            params = tool["params_model"](**args)
        except Exception as e:
            return f"Eroare validare parametri pentru '{name}': {e}"

        # Pasul 3 + 4: Execute + Return
        # Analogie DE: ca rularea efectivă a unui ETL job
        # dacă funcția eșuează → returnăm eroare human-readable
        # (LLM-ul nu înțelege stack traces — principiu din S6.6 din curs)
        try:
            return str(tool["func"](params))
        except Exception as e:
            return f"Eroare execuție '{name}': {e}"


    @staticmethod
    def catalog() -> list[dict]:
        """
        Generează catalogul tool-urilor în format JSON Schema pentru LLM.
        
        Analogie DE: ca INFORMATION_SCHEMA din BigQuery
        — expune structura și descrierea fiecărui tabel (tool)
        astfel încât LLM-ul să știe:
        1. Ce tool-uri există
        2. Ce parametri acceptă fiecare
        3. Ce face fiecare tool
        
        Pydantic generează automat JSON Schema din params_model
        — zero cod extra, zero duplicare
        """

        # Iterează prin TOOL_REGISTRY și construiește catalogul
        # Analogie DE: ca un SELECT * FROM information_schema.tables
        # — returnează metadata despre fiecare tool
        return [
            {
                # Numele tool-ului — LLM îl folosește să îl apeleze
                "name": name,

                # Descrierea — LLM citește asta ca să decidă CÂND să îl apeleze
                # vine din docstring-ul funcției (validat în registry.py)
                "description": tool["description"],

                # JSON Schema generată automat din clasa Pydantic
                # Analogie DE: ca schema unui tabel BigQuery
                # — LLM știe exact ce parametri să trimită și de ce tip
                "input_schema": tool["params_model"].model_json_schema(),
            }
            for name, tool in TOOL_REGISTRY.items()
        ]