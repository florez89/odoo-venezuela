"""A quotation whose rate in force is older than `rate_max_age_days` shows a banner.

Only a banner: confirming an order posts nothing and its invoice takes, and warns
about, its own rate.
"""

from datetime import date, datetime

from odoo.tests import TransactionCase, freeze_time, tagged


@tagged("post_install", "-at_install", "l10n_ve_sale")
class TestSaleOrderRateAge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.usd = cls.env.ref("base.USD")
        cls.company.currency_id = cls.env.ref("base.VEF")
        cls.company.foreign_currency_id = cls.usd
        cls.company.rate_max_age_days = 2
        cls.env.user.tz = "America/Caracas"
        cls.env = cls.env(context=dict(cls.env.context, tz="America/Caracas"))
        cls.env["res.currency.rate"].search(
            [("currency_id", "=", cls.usd.id), ("name", ">=", date(2026, 10, 26))]
        ).unlink()
        cls.env["res.currency.rate"].create(
            {
                "name": date(2026, 10, 26),
                "currency_id": cls.usd.id,
                "company_id": cls.company.id,
                "company_rate": 1.0 / 40.0,
                "inverse_company_rate": 40.0,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Partner Rate Age"})

    def _order(self, when):
        return self.env["sale.order"].create({"partner_id": self.partner.id, "date_order": when})

    @freeze_time("2026-10-26 15:00:00")
    def test_rate_of_the_same_day_is_not_outdated(self):
        order = self._order(datetime(2026, 10, 26, 15, 0, 0))
        self.assertEqual(order.foreign_rate_used_date, date(2026, 10, 26))
        self.assertFalse(order.is_foreign_rate_outdated)

    @freeze_time("2026-10-30 15:00:00")
    def test_rate_older_than_the_limit_is_outdated(self):
        order = self._order(datetime(2026, 10, 30, 15, 0, 0))
        self.assertEqual(order.foreign_rate_used_date, date(2026, 10, 26))
        self.assertEqual(order.foreign_rate_age_days, 4)
        self.assertTrue(order.is_foreign_rate_outdated)

    @freeze_time("2026-10-30 15:00:00")
    def test_rate_set_on_purpose_never_warns(self):
        order = self._order(datetime(2026, 10, 30, 15, 0, 0))
        order.write({"manually_set_rate": True, "foreign_rate": 50.0, "foreign_inverse_rate": 1 / 50.0})
        self.assertFalse(order.is_foreign_rate_outdated)

    @freeze_time("2026-10-30 15:00:00")
    def test_outdated_rate_does_not_block_confirmation(self):
        order = self._order(datetime(2026, 10, 30, 15, 0, 0))
        order.order_line = [
            (0, 0, {"product_id": self.env["product.product"].create(
                {"name": "Service Rate Age", "type": "service", "list_price": 10.0}
            ).id})
        ]
        order.action_confirm()
        self.assertEqual(order.state, "sale")
