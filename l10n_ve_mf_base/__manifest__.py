{
    "name": "Venezuela - Máquina Fiscal (Base Web Serial)",
    "summary": "Driver base Web Serial API para impresoras fiscales The Factory HKA (TFHKA).",
    "license": "LGPL-3",
    "category": "Accounting",
    "version": "19.0.1.1.3",
    "author": "Gustavo Florez, Binaural",
    "maintainers": ["florez89"],
    "website": "https://github.com/florez89/odoo-venezuela",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "l10n_ve_mf_base/static/src/core/*.js",
            "l10n_ve_mf_base/static/src/drivers/*.js",
        ],
        "web.assets_unit_tests": [
            "l10n_ve_mf_base/static/tests/unit/**/*",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
