from odoo.addons.l10n_ve_accountant import add_foreign_rate_date_column


def migrate(cr, version):
    add_foreign_rate_date_column(cr)
