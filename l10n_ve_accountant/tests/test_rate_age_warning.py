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

from .common_rate_age import RATE_DAY, RateAgeMixin


@tagged("post_install", "-at_install", "l10n_ve_accountant")
class TestRateAgeWarning(RateAgeMixin, TransactionCase):
    def setUp(self):
        super().setUp()
        self._setup_rate_age()
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
        return self.env["account.move"].create(
            {
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
        )

    def _rate_notes(self, move):
        return move.message_ids.filtered(lambda m: "days old" in (m.body or ""))

    def test_rate_of_the_same_day_is_not_outdated(self):
        bill = self._bill(RATE_DAY)
        self.assertEqual(bill.foreign_rate_date, RATE_DAY)
        self.assertEqual(bill.foreign_rate_age_days, 0)
        self.assertFalse(bill.is_foreign_rate_outdated)

    def test_rate_at_the_limit_is_not_outdated(self):
        bill = self._bill(date(2026, 3, 12))
        self.assertEqual(bill.foreign_rate_date, RATE_DAY)
        self.assertEqual(bill.foreign_rate_age_days, 2)
        self.assertFalse(bill.is_foreign_rate_outdated)

    def test_rate_older_than_the_limit_is_outdated(self):
        bill = self._bill(date(2026, 3, 13))
        self.assertEqual(bill.foreign_rate_date, RATE_DAY)
        self.assertEqual(bill.foreign_rate_age_days, 3)
        self.assertTrue(bill.is_foreign_rate_outdated)

    def test_zero_limit_disables_the_warning(self):
        self.company.rate_max_age_days = 0
        bill = self._bill(date(2026, 3, 13))
        self.assertFalse(bill.is_foreign_rate_outdated)

    def test_rate_typed_by_hand_never_warns(self):
        bill = self._bill(date(2026, 3, 13))
        bill.write({"manually_set_rate": True, "foreign_rate": 50.0, "foreign_inverse_rate": 1 / 50.0})
        bill.invoice_date = date(2026, 3, 13)  # recompute: the typed rate stays
        bill._compute_rate()
        self.assertFalse(bill.foreign_rate_date)
        self.assertFalse(bill.is_foreign_rate_outdated)

    def test_posting_from_the_form_asks_for_confirmation(self):
        bill = self._bill(date(2026, 3, 13))
        action = bill.with_context(l10n_ve_check_rate_age=True).action_post()
        self.assertEqual(action["res_model"], "move.action.post.alert.wizard")
        self.assertEqual(bill.state, "draft")

        wizard = self.env["move.action.post.alert.wizard"].with_context(action["context"]).create({})
        self.assertTrue(wizard.is_foreign_rate_outdated)
        self.assertEqual(wizard.foreign_rate_age_days, 3)
        self.assertFalse(wizard.is_customer_invoice)
        wizard.action_confirm()
        self.assertEqual(bill.state, "posted")
        self.assertEqual(len(self._rate_notes(bill)), 1)

    def test_posting_from_the_form_without_outdated_rate_does_not_ask(self):
        bill = self._bill(RATE_DAY)
        bill.with_context(l10n_ve_check_rate_age=True).action_post()
        self.assertEqual(bill.state, "posted")

    def test_automatic_posting_is_not_blocked_and_is_recorded(self):
        bill = self._bill(date(2026, 3, 13))
        bill.action_post()
        self.assertEqual(bill.state, "posted")
        notes = self._rate_notes(bill)
        self.assertEqual(len(notes), 1)
        self.assertIn(format_date(self.env, RATE_DAY), notes.body)

    def test_posting_with_a_recent_rate_leaves_no_note(self):
        bill = self._bill(RATE_DAY)
        bill.action_post()
        self.assertFalse(self._rate_notes(bill))

    def test_confirm_button_keeps_the_core_context(self):
        arch = self.env["account.move"].get_view(
            self.env.ref("account.view_move_form").id, "form"
        )["arch"]
        self.assertIn("'disable_abnormal_invoice_detection': False", arch)
        self.assertIn("'l10n_ve_check_rate_age': True", arch)
