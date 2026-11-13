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

    def test_seed_tax_unit_does_not_block_today(self):
        """The l10n_ve_accountant placeholder unit gets a historic date, so a
        unit published on the installation day can be created."""
        seed = self.env.ref("l10n_ve_accountant.tax_unit_data_l10n_ve_payment_extension")
        self.assertEqual(seed.available_date, fields.Date.to_date("2000-01-01"))
        unit = self.env["tax.unit"].create({"name": "9,00", "value": 9.0})
        self.assertEqual(unit.available_date, fields.Date.context_today(unit))
