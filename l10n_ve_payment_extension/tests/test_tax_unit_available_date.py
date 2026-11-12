from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTaxUnitAvailableDate(TransactionCase):
    def test_no_tax_unit_without_available_date(self):
        """Records created before this module adds `available_date` (e.g. the
        l10n_ve_accountant data record) must get a date, otherwise the
        NOT NULL constraint cannot be applied and the "latest unit" ordering
        breaks."""
        self.env.cr.execute("SELECT count(*) FROM tax_unit WHERE available_date IS NULL")
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_new_tax_unit_defaults_available_date(self):
        defaults = self.env["tax.unit"].default_get(["available_date"])
        self.assertEqual(defaults.get("available_date"), fields.Date.context_today(self.env.user))
