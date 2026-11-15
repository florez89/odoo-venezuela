{
    "name": "Venezuela - The Factory HKA / Guía de Despacho",
    "license": "LGPL-3",
    "author": "Gustavo Florez, Binaural",
    "maintainers": ["florez89"],
    "website": "https://github.com/florez89/odoo-venezuela",
    "category": "Accounting/Accounting",
    "version": "19.0.1.2.2",
    "depends": [
        "l10n_ve_invoice_digital",
        "l10n_ve_stock_account",
        "stock",
    ],
    "external_dependencies": {"python": ["requests", "pytz"]},
    "images": ["static/description/icon.png"],
    "application": True,
    "data": [
        "views/stock_picking.xml",
    ],
}
