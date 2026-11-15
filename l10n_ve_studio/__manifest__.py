{
    "name": "Venezuela - Studio",
    "summary": """
        Limitación de Odoo-Studio para la localización en Venezuela
    """,
    "license": "LGPL-3",
    "author": "Gustavo Florez, Binaural",
    "maintainers": ["florez89"],
    "website": "https://github.com/florez89/odoo-venezuela",
    "category": "Base",
    "version": "19.0.1.0.0",
    # any module necessary for this one to work correctly
    "depends": ["l10n_ve_base"],
    "data": [],
    "images": ["static/description/icon.png"],
    "application": True,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}
