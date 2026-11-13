from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "l10n_ve_rate")
class TestRateInForce(TransactionCase):
    """compute_rate uses the rate in force (latest on or before the date) and can
    report its date; the company limits how old that rate may be."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rate = cls.env["res.currency.rate"]
        cls.usd = cls.env.ref("base.USD")
        cls.company = cls.env.company
        cls.company.write(
            {"currency_id": cls.env.ref("base.VEF").id, "foreign_currency_id": cls.usd.id}
        )
        cls.Rate.search([("currency_id", "=", cls.usd.id)]).unlink()

    def _create_rate(self, day, inverse_rate):
        return self.Rate.create(
            {
                "name": day,
                "currency_id": self.usd.id,
                "company_id": self.company.id,
                "inverse_company_rate": inverse_rate,
            }
        )

    def test_compute_rate_returns_the_date_of_the_rate_used(self):
        jan = self._create_rate(date(2023, 1, 1), 40.0)
        result = self.Rate.compute_rate(self.usd.id, date(2023, 6, 1), with_rate_date=True)
        self.assertEqual(result["foreign_rate"], jan.inverse_company_rate)
        self.assertEqual(result["foreign_inverse_rate"], jan.company_rate)
        self.assertEqual(result["rate_date"], jan.name)

    def test_compute_rate_omits_the_date_by_default(self):
        """Callers write the result into records: an extra key would break them."""
        self._create_rate(date(2023, 6, 1), 45.0)
        result = self.Rate.compute_rate(self.usd.id, date(2023, 6, 1))
        self.assertEqual(set(result), {"foreign_rate", "foreign_inverse_rate"})

    def test_future_fallback_reports_the_date_of_that_rate(self):
        """Without any rate on or before the date, Odoo 18 VE keeps falling back to
        the earliest later rate (like native Odoo); the date reported is its own."""
        later = self._create_rate(date(2023, 12, 1), 50.0)
        result = self.Rate.compute_rate(self.usd.id, date(2023, 6, 1), with_rate_date=True)
        self.assertEqual(result["foreign_rate"], later.inverse_company_rate)
        self.assertEqual(result["rate_date"], later.name)

    def test_no_rate_at_all_returns_empty(self):
        self.assertEqual(
            self.Rate.compute_rate(self.usd.id, date(2023, 6, 1), with_rate_date=True), {}
        )

    def test_rate_in_force_date_only_when_the_document_uses_it(self):
        rate = self._create_rate(date(2023, 6, 1), 45.0)
        in_force = self.Rate.compute_rate(self.usd.id, date(2023, 6, 3))
        self.assertEqual(
            self.Rate.get_rate_in_force_date(
                self.usd.id, date(2023, 6, 3), in_force["foreign_inverse_rate"]
            ),
            rate.name,
        )
        # a rate typed by hand is not the rate in force: nothing to age
        self.assertFalse(self.Rate.get_rate_in_force_date(self.usd.id, date(2023, 6, 3), 1 / 99.0))
        self.assertFalse(self.Rate.get_rate_in_force_date(False, date(2023, 6, 3), 1 / 45.0))

    def test_rate_max_age_days_defaults_to_two(self):
        self.assertEqual(self.env["res.company"].new({}).rate_max_age_days, 2)

    def test_rate_max_age_days_is_editable_from_settings(self):
        settings = self.env["res.config.settings"].create({"rate_max_age_days": 5})
        settings.execute()
        self.assertEqual(self.company.rate_max_age_days, 5)

    def test_rate_max_age_days_cannot_be_negative(self):
        with self.assertRaises(ValidationError):
            self.company.rate_max_age_days = -1
