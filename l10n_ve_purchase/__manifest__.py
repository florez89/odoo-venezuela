{
    "name": "Venezuela - Compras",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "summary": "Módulo para gestionar compras en Venezuela",
    "description": """
        Este módulo personaliza el proceso de gestión de compras para cumplir con las regulaciones venezolanas.
    """,
    "author": "Gustavo Florez, Binaural",
    "maintainers": ["florez89"],
    "website": "https://github.com/florez89/odoo-venezuela",
    "category": "Purchase",
    "depends": ["purchase", "account"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "application": True,
    "images": ["static/description/icon.png"],
}

