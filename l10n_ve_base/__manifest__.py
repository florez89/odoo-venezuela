{
    "name": "Venezuela - Base",
    "summary": """
        Módulo Base de la localización de Venezuela
    """,
    "license": "LGPL-3",
    "author": "Gustavo Florez, Binaural",
    "maintainers": ["florez89"],
    "website": "https://github.com/florez89/odoo-venezuela",
    "category": "Technical",
    "version": "19.0.1.0.2",
    "depends": ["base", "web"],
    "auto_install": False,
    "data": ["security/ir.model.access.csv", "views/res_config_settings_views.xml"],
    "assets": {
        "web.assets_backend": [
            "l10n_ve_base/static/src/core/debug/debug_menu_items.js",
        ],
    },
}
