"""A document whose rate is older than `rate_max_age_days` warns but is not blocked.

The rate in force is the latest one on or before the document date. When it is
older than the company limit the draft shows a warning, posting from the form
asks for confirmation and the posted document records it in its chatter.
Automatic flows (code calling `action_post`) are never stopped.
"""

from datetime import date

from odoo import Command
from odoo.tests import TransactionCase, tagged
from odoo.tools import format_date

from .common_tz_boundary import CARACAS_DAY, TzBoundaryMixin, freeze_time


@tagged("post_install", "-at_install", "l10n_ve_accountant_rate_age")
class TestRateAgeWarning(TzBoundaryMixin, TransactionCase):
    def setUp(self):
        super().setUp()
        # today is 2026-03-13 in Caracas; USD rates exist up to CARACAS_DAY (2026-03-10)
        self.enterContext(freeze_time("2026-03-13 15:00:00"))
        self._setup_tz_boundary()
        self.company.rate_max_age_days = 2
        self.partner = self.env["res.partner"].create({"name": "Rate Age Vendor"})
        self.journal = self.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", self.company.id)], limit=1
        )
        self.expense_account = self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(self.company),
                ("account_type", "=", "expense"),
            ],
            limit=1,
        )
        # Venezuelan invoices need a tax on every product line
        self.exempt_tax = self.env["account.tax"].create(
            {
                "name": "Rate Age Exempt",
                "amount": 0.0,
                "type_tax_use": "purchase",
                "company_id": self.company.id,
                "country_id": self.company.account_fiscal_country_id.id,
            }
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Rate Age Service",
                "type": "service",
                "property_account_expense_id": self.expense_account.id,
                "supplier_taxes_id": [Command.set(self.exempt_tax.ids)],
            }
        )

    def _bill(self, invoice_date):
        Move = self.env["account.move"]
        vals = {
            "move_type": "in_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "invoice_date": invoice_date,
            "date": invoice_date,
            "correlative": "RA-%s" % invoice_date,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": self.product.id,
                        "name": "Service",
                        "quantity": 1,
                        "price_unit": 100.0,
                        "account_id": self.expense_account.id,
                        "tax_ids": [Command.set(self.exempt_tax.ids)],
                    }
                )
            ],
        }
        if "invoice_date_display" in Move._fields:  # l10n_ve_invoice: shown date, today by default
            vals["invoice_date_display"] = invoice_date
        return Move.create(vals)

    def test_rate_of_the_same_day_is_not_outdated(self):
        bill = self._bill(CARACAS_DAY)
        self.assertEqual(bill.foreign_rate_date, CARACAS_DAY)
        self.assertEqual(bill.foreign_rate_age_days, 0)
        self.assertFalse(bill.is_foreign_rate_outdated)

    def test_rate_at_the_limit_is_not_outdated(self):
        bill = self._bill(date(2026, 3, 12))
        self.assertEqual(bill.foreign_rate_date, CARACAS_DAY)
        self.assertEqual(bill.foreign_rate_age_days, 2)
        self.assertFalse(bill.is_foreign_rate_outdated)

    def test_rate_older_than_the_limit_is_outdated(self):
        bill = self._bill(date(2026, 3, 13))
        self.assertEqual(bill.foreign_rate_date, CARACAS_DAY)
        self.assertEqual(bill.foreign_rate_age_days, 3)
        self.assertTrue(bill.is_foreign_rate_outdated)

    def test_zero_limit_disables_the_warning(self):
        self.company.rate_max_age_days = 0
        bill = self._bill(date(2026, 3, 13))
        self.assertFalse(bill.is_foreign_rate_outdated)

    def test_posting_from_the_form_asks_for_confirmation(self):
        bill = self._bill(date(2026, 3, 13))
        action = bill.with_context(l10n_ve_check_rate_age=True).action_post()
        self.assertEqual(action["res_model"], "move.action.post.alert.wizard")
        self.assertEqual(bill.state, "draft")

        wizard = self.env["move.action.post.alert.wizard"].with_context(action["context"]).create({})
        self.assertTrue(wizard.is_foreign_rate_outdated)
        self.assertEqual(wizard.foreign_rate_age_days, 3)
        wizard.action_confirm()
        self.assertEqual(bill.state, "posted")
        self.assertIn("3 days old", bill.message_ids[0].body)

    def test_posting_from_the_form_without_outdated_rate_does_not_ask(self):
        bill = self._bill(CARACAS_DAY)
        bill.with_context(l10n_ve_check_rate_age=True).action_post()
        self.assertEqual(bill.state, "posted")

    def test_automatic_posting_is_not_blocked_and_is_recorded(self):
        bill = self._bill(date(2026, 3, 13))
        bill.action_post()
        self.assertEqual(bill.state, "posted")
        notes = bill.message_ids.filtered(lambda m: "days old" in (m.body or ""))
        self.assertEqual(len(notes), 1)
        self.assertIn(format_date(self.env, CARACAS_DAY), notes.body)

    def test_posting_with_a_recent_rate_leaves_no_note(self):
        bill = self._bill(CARACAS_DAY)
        bill.action_post()
        self.assertFalse(bill.message_ids.filtered(lambda m: "days old" in (m.body or "")))
