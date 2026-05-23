# tools/basic_tools.py
import json
import os
import time
from datetime import datetime
from pathlib import Path

from google import genai
import pypdf

from tools.params_models import (
    CalculatorParams,
    DateParams,
    ExtractInvoiceParams,
    ReadPDFParams,
)
from tools.registry import register_tool

_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


# ─── TOOL 1: Calculator ──────────────────────────────────────────────────────
@register_tool
def calculator(params: CalculatorParams) -> str:
    """Evaluează o expresie matematică simplă cu operatori +, -, *, /.
    Folosește pentru calcule numerice exacte, sume de facturi, conversii valutare.
    NU folosi pentru text sau logică non-numerică."""

    allowed = set("0123456789+-*/(). ")
    if not all(c in allowed for c in params.expression):
        return "Eroare: expresie invalida — caractere nepermise."

    try:
        result = eval(params.expression)
        return f"Rezultat: {result}"
    except Exception as e:
        return f"Eroare calcul: {str(e)}"


# ─── TOOL 2: Data curenta ────────────────────────────────────────────────────
@register_tool
def get_current_date(params: DateParams) -> str:
    """Returnează data curentă în formatul specificat (implicit YYYY-MM-DD).
    Folosește când userul întreabă data de azi sau când ai nevoie de timestamp."""

    fmt = params.format or "%Y-%m-%d"
    return datetime.now().strftime(fmt)


# ─── TOOL 3: Citire PDF brut ─────────────────────────────────────────────────
@register_tool
def read_pdf(params: ReadPDFParams) -> str:
    """Citește și extrage textul brut dintr-un fișier PDF (facturi, contracte).
    Returnează textul complet al documentului, pagină cu pagină.
    Folosește înainte de extract_invoice pentru a vedea conținutul raw.
    NU funcționează cu PDF-uri scanate (imagini) — doar text searchable."""

    path = Path(params.file_path)

    if not path.exists():
        return f"Eroare: fisierul '{params.file_path}' nu exista."
    if path.suffix.lower() != ".pdf":
        return f"Eroare: '{params.file_path}' nu este un fisier PDF."

    try:
        reader = pypdf.PdfReader(str(path))
        pages_text = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(f"=== Pagina {i + 1} ===\n{text.strip()}")

        if not pages_text:
            return "PDF-ul nu contine text extractibil (posibil scanat/imagine)."

        full_text = "\n\n".join(pages_text)

        return (
            f"PDF: {path.name} | {len(reader.pages)} pagini\n\n"
            f"{full_text}"
        )

    except pypdf.errors.PdfReadError as e:
        return f"Eroare citire PDF (corupt sau protejat): {str(e)}"
    except Exception as e:
        return f"Eroare neasteptata: {str(e)}"


# ─── TOOL 4: Extragere structurata factura ───────────────────────────────────
@register_tool
def extract_invoice(params: ExtractInvoiceParams) -> str:
    """Extrage date structurate dintr-o factură PDF și salvează JSON.
    Funcționează cu orice tip de factură: produse (ex: Taste Crafters OTG69224)
    sau servicii telecom (ex: Orange JAT018210809).
    Returnează JSON cu: numar, data, furnizor, client, total, produse/servicii.
    Folosește DUPĂ ce știi că fișierul există și este un PDF valid."""

    path = Path(params.file_path)

    if not path.exists():
        return f"Eroare: fisierul '{params.file_path}' nu exista."

    # ── EXTRACT: citim PDF-ul cu pypdf ────────────────────────────────────────
    try:
        reader = pypdf.PdfReader(str(path))
        pages_text = []

        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text.strip())

        raw_text = "\n\n".join(pages_text)

        if not raw_text.strip():
            return "Eroare: PDF-ul nu contine text extractibil."

    except Exception as e:
        return f"Eroare citire PDF: {str(e)}"

    # ── TRANSFORM: LLM transforma textul brut in JSON structurat ─────────────
    prompt = f"""Ești un expert în procesarea facturilor românești.
Extrage datele din factura de mai jos și returnează STRICT un JSON valid,
fără text suplimentar, fără markdown, fără explicații.

Schema JSON obligatorie:
{{
  "numar_factura": "string",
  "data_emitere": "string — format YYYY-MM-DD sau cum apare in document",
  "furnizor": "string — compania care emite factura",
  "client": "string — compania sau persoana facturata",
  "total_fara_tva": "float",
  "tva": "float",
  "total_cu_tva": "float",
  "moneda": "string — RON sau EUR",
  "tip_factura": "string — produse / servicii / mixt",
  "linii": [
    {{
      "descriere": "string",
      "cantitate": "float",
      "pret_unitar": "float",
      "total_linie": "float"
    }}
  ]
}}

TEXT FACTURA:
{raw_text}
"""

    time.sleep(3)

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw_json = response.text.strip()

        # curatam markdown daca LLM-ul l-a adaugat
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]
            raw_json = raw_json.strip()

        invoice_data = json.loads(raw_json)

    except json.JSONDecodeError as e:
        return f"Eroare: LLM-ul nu a returnat JSON valid. Detalii: {str(e)}"
    except Exception as e:
        return f"Eroare la apelul LLM: {str(e)}"

    # ── LOAD: scriem JSON pe disc ─────────────────────────────────────────────
    try:
        output_dir = Path(params.output_dir or "extracted_data/facturi")
        output_dir.mkdir(parents=True, exist_ok=True)

        numar = invoice_data.get("numar_factura", path.stem)
        safe_name = "".join(c for c in numar if c.isalnum() or c in "-_")
        output_path = output_dir / f"{safe_name}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(invoice_data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        return (
            f"Extractie reusita dar eroare la salvare ({str(e)}):\n"
            f"{json.dumps(invoice_data, ensure_ascii=False, indent=2)}"
        )

    return (
        f"Factura procesata cu succes!\n"
        f"  Numar:    {invoice_data.get('numar_factura', 'N/A')}\n"
        f"  Furnizor: {invoice_data.get('furnizor', 'N/A')}\n"
        f"  Total:    {invoice_data.get('total_cu_tva', 'N/A')} "
        f"{invoice_data.get('moneda', 'RON')}\n"
        f"  Linii:    {len(invoice_data.get('linii', []))}\n"
        f"  Salvat:   {output_path}"
    )