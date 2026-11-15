from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "l10n_ve_accountant_payment_zero")
class TestPaymentZeroAmount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Bank payments need an outstanding account (enforced by
        # account.payment.action_post); configure it like a user would.
        company = cls.env.company
        chart = cls.env["account.chart.template"].with_company(company)
        outstanding_in = chart.ref("account_journal_payment_debit_account_id", raise_if_not_found=False)
        outstanding_out = chart.ref("account_journal_payment_credit_account_id", raise_if_not_found=False)
        for journal in cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", company.id)]
        ):
            journal.inbound_payment_method_line_ids.filtered(
                lambda line: not line.payment_account_id
            ).payment_account_id = outstanding_in or journal.default_account_id
            journal.outbound_payment_method_line_ids.filtered(
                lambda line: not line.payment_account_id
            ).payment_account_id = outstanding_out or journal.default_account_id

    def _create_payment(self, amount):
        partner = self.env["res.partner"].create({"name": "Partner Zero Amount"})
        journal = self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        return self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": partner.id,
                "journal_id": journal.id,
                "amount": amount,
            }
        )

    def test_post_zero_amount_raises(self):
        payment = self._create_payment(0.0)
        with self.assertRaises(UserError):
            payment.action_post()
        self.assertEqual(payment.state, "draft")

    def test_post_positive_amount_ok(self):
        payment = self._create_payment(100.0)
        payment.action_post()
        self.assertNotEqual(payment.state, "draft")

    def test_post_zero_amount_from_pos_is_exempt(self):
        """El cierre de sesión POS agrupa pagos por neto y puede netear 0."""
        payment = self._create_payment(0.0)
        payment.with_context(from_pos=True).action_post()
        self.assertNotEqual(payment.state, "draft")
