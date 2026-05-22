# prompts/registry.py
# Incarca toate fisierele YAML din prompts/ si le pune la dispozitie
# Analogie dbt: e ca dbt_project.yml — stie unde sunt toate "modelele" (prompt-urile)

import yaml
from pathlib import Path
from jinja2 import Template


class PromptRegistry:

    def __init__(self, folder: str = "prompts"):
        self._folder = Path(folder)
        self._templates = self._load()

    def _load(self) -> dict:
        """Citeste toate .yaml din folder si le stocheaza in dict {name: data}."""
        templates = {}
        for path in self._folder.glob("*.yaml"):
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                templates[data["name"]] = data
        return templates

    def render(self, name: str, **variables) -> str:
        """Returneaza prompt-ul randat cu Jinja2 (inlocuieste {{ variabile }})."""
        if name not in self._templates:
            available = list(self._templates.keys())
            raise KeyError(f"Prompt '{name}' nu exista. Disponibile: {available}")

        template_str = self._templates[name]["prompt"]
        return Template(template_str).render(**variables)

    def list_templates(self) -> list:
        """Lista tuturor prompt-urilor incarcate."""
        return list(self._templates.keys())