from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from .common_rates import set_rate


@tagged("post_install", "-at_install")
class TestForeignCurrencyWriteGuard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        Currency = cls.env["res.currency"].with_context(active_test=False)
        cls.usd = Currency.search([("name", "=", "USD")], limit=1)
        cls.eur = Currency.search([("name", "=", "EUR")], limit=1)
        (cls.usd | cls.eur).write({"active": True})
        if cls.company.currency_id == cls.usd:
            cls.usd, cls.eur = cls.eur, cls.usd
        cls.company.foreign_currency_id = cls.usd
        set_rate(cls.env, cls.usd, fields.Date.context_today(cls.env.user), cls.company, 400.0)
        journal = cls.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", cls.company.id)], limit=1
        )
        accounts = cls.env["account.account"].search(
            [("company_ids", "in", cls.company.id), ("account_type", "=", "asset_current")], limit=2
        )
        cls.env["account.move"].create({
            "move_type": "entry",
            "journal_id": journal.id,
            "line_ids": [
                (0, 0, {"account_id": accounts[0].id, "debit": 100.0}),
                (0, 0, {"account_id": accounts[1].id, "credit": 100.0}),
            ],
        })

    def test_rewrite_same_foreign_currency_is_allowed(self):
        self.company.write({"foreign_currency_id": self.usd.id})
        self.assertEqual(self.company.foreign_currency_id, self.usd)

    def test_change_used_foreign_currency_is_blocked(self):
        with self.assertRaises(ValidationError):
            self.company.write({"foreign_currency_id": self.eur.id})
