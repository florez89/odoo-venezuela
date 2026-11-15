"""A payment whose rate in force is older than `rate_max_age_days` warns but is not blocked."""

from datetime import date

from odoo.tests import TransactionCase, tagged
from odoo.tools import format_date

from .common_tz_boundary import CARACAS_DAY, TzBoundaryMixin, freeze_time


@tagged("post_install", "-at_install", "l10n_ve_accountant_rate_age")
class TestPaymentRateAgeWarning(TzBoundaryMixin, TransactionCase):
    def setUp(self):
        super().setUp()
        # today is 2026-03-13 in Caracas; USD rates exist up to CARACAS_DAY (2026-03-10)
        self.enterContext(freeze_time("2026-03-13 15:00:00"))
        self._setup_tz_boundary()
        self.company.rate_max_age_days = 2
        self.partner = self.env["res.partner"].create({"name": "Rate Age Customer"})
        self.journal = self.env["account.journal"].search(
            [("type", "=", "cash"), ("company_id", "=", self.company.id)], limit=1
        ) or self.env["account.journal"].create(
            {"name": "Rate Age Cash", "code": "RACSH", "type": "cash", "company_id": self.company.id}
        )

    def _payment(self, payment_date, **vals):
        return self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "amount": 100.0,
                "date": payment_date,
                **vals,
            }
        )

    def _rate_notes(self, payment):
        return payment.message_ids.filtered(lambda m: "days old" in (m.body or ""))

    def test_rate_of_the_same_day_is_not_outdated(self):
        payment = self._payment(CARACAS_DAY)
        self.assertEqual(payment.foreign_rate_date, CARACAS_DAY)
        self.assertFalse(payment.is_foreign_rate_outdated)

    def test_rate_older_than_the_limit_is_outdated(self):
        payment = self._payment(date(2026, 3, 13))
        self.assertEqual(payment.foreign_rate_date, CARACAS_DAY)
        self.assertEqual(payment.foreign_rate_age_days, 3)
        self.assertTrue(payment.is_foreign_rate_outdated)

    def test_rate_set_on_purpose_never_warns(self):
        payment = self._payment(date(2026, 3, 13))
        payment.foreign_inverse_rate = 1 / 50.0
        self.assertFalse(payment.foreign_rate_date)
        self.assertFalse(payment.is_foreign_rate_outdated)

    def test_confirming_from_the_form_asks_for_confirmation(self):
        payment = self._payment(date(2026, 3, 13))
        action = payment.with_context(l10n_ve_check_rate_age=True).action_post()
        self.assertEqual(action["res_model"], "account.payment.rate.age.wizard")
        self.assertEqual(payment.state, "draft")

        wizard = self.env[action["res_model"]].with_context(action["context"]).create({})
        self.assertEqual(wizard.outdated_payment_ids, payment)
        wizard.action_confirm()
        self.assertNotEqual(payment.state, "draft")
        self.assertEqual(len(self._rate_notes(payment)), 1)

    def test_confirming_from_the_form_without_outdated_rate_does_not_ask(self):
        payment = self._payment(CARACAS_DAY)
        payment.with_context(l10n_ve_check_rate_age=True).action_post()
        self.assertNotEqual(payment.state, "draft")
        self.assertFalse(self._rate_notes(payment))

    def test_automatic_posting_is_not_blocked_and_is_recorded(self):
        payment = self._payment(date(2026, 3, 13))
        payment.action_post()
        self.assertNotEqual(payment.state, "draft")
        notes = self._rate_notes(payment)
        self.assertEqual(len(notes), 1)
        self.assertIn(format_date(self.env, CARACAS_DAY), notes.body)
