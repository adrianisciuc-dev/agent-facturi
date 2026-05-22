from pydantic import BaseModel, Field


# Parametrii pentru listarea facturilor dintr-un folder
# Folosit când agentul vrea să vadă ce fișiere PDF există disponibile
class ListInvoicesParams(BaseModel):
    folder: str = Field(
        default="invoices",
        description="Folderul unde se află facturile PDF"
    )


# Parametrii pentru citirea/extragerea textului dintr-o factură PDF
# Folosit când agentul vrea să citească conținutul unui fișier specific
class ReadInvoiceParams(BaseModel):
    filename: str = Field(
        description="Numele fișierului PDF din folderul invoices"
    )


# Parametrii pentru calculul minutelor dintr-o factură de telefonie
# Folosit când agentul analizează facturi de tip telecom (ex: Orange, Vodafone)
class CalculateMinutesParams(BaseModel):
    filename: str = Field(
        description="Numele fișierului PDF cu factura de telefonie"
    )
    phone_number: str = Field(
        description="Numărul de telefon pentru care calculăm minutele"
    )


# Parametrii pentru calculul totalului unui produs dintr-o factură
# Folosit când agentul caută un produs specific și sumează cantitate * preț
class CalculateProductTotalParams(BaseModel):
    filename: str = Field(
        description="Numele fișierului PDF din folderul invoices"
    )
    product_name: str = Field(
        description="Numele produsului căutat în factură"
    )


# Parametrii pentru generarea unui grafic din datele extrase
# Folosit când agentul vizualizează comparații sau evoluții din facturi
class GenerateChartParams(BaseModel):
    data: str = Field(
        description="Datele pentru grafic"
    )
    chart_type: str = Field(
        default="bar",
        description="Tipul graficului: bar, pie, line",
        pattern=r"^(bar|pie|line)$"
    )


# Parametrii pentru exportul datelor extrase într-un fișier
# Folosit când agentul salvează rezultatele analizei pentru utilizator
class ExportDataParams(BaseModel):
    filename: str = Field(
        description="Numele fișierului de export"
    )
    format: str = Field(
        default="xlsx",
        description="Formatul exportului: xlsx, csv, json",
        pattern=r"^(xlsx|csv|json)$"
    )