from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_ve_pos.tests.common import VePosHttpCommon


@tagged("post_install", "-at_install", "l10n_ve_pos_igtf")
class TestVePosIgtfTours(VePosHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.igtf_account = cls.env["account.account"].create(
            {"code": "X236IGTF", "name": "IGTF Clientes - Test", "account_type": "liability_current"}
        )
        cls.company.write({"igtf_percentage": 3.0, "customer_account_igtf_id": cls.igtf_account.id})
        cls.usd_bank_journal = cls.env["account.journal"].create(
            {"name": "Bank USD IGTF Test", "type": "bank", "code": "VBKU"}
        )
        cls.igtf_method = cls.env["pos.payment.method"].create(
            {
                "name": "USD IGTF",
                "journal_id": cls.usd_bank_journal.id,
                "outstanding_account_id": cls.outstanding_account.id,
                "is_foreign_currency": True,
                "apply_igtf": True,
            }
        )
        cls.pos_config.payment_method_ids = [Command.link(cls.igtf_method.id)]

    def test_01_igtf_on_foreign_currency_payment(self):
        """Paying with a foreign currency method that applies IGTF charges 3% of
        the base it pays on top of the invoice total."""
        self.start_ve_pos_tour("l10n_ve_pos_igtf_payment_tour")

        order = self.last_order()
        self.assertTrue(order, "The tour must create an order")
        self.assertIn(order.state, ("paid", "done", "invoiced"))
        self.assertAlmostEqual(order.amount_total, 116.0, places=2)
        self.assertAlmostEqual(order.igtf_amount, 3.48, places=2)
        self.assertAlmostEqual(order.bi_igtf, 116.0, places=2)
        self.assertAlmostEqual(order.amount_paid, 119.48, places=2)

        payment = order.payment_ids.filtered(lambda p: p.payment_method_id == self.igtf_method)
        self.assertTrue(payment.include_igtf)
        self.assertAlmostEqual(payment.amount, 119.48, places=2)
        self.assertAlmostEqual(payment.igtf_amount, 3.48, places=2)
        self.assertAlmostEqual(payment.foreign_igtf_amount, 0.09, places=2)

        invoice = order.account_move
        self.assertTrue(invoice)
        self.assertAlmostEqual(invoice.amount_total, 116.0, places=2)
        self.assertAlmostEqual(invoice.bi_igtf, 116.0, places=2)
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))
        igtf_lines = payment.account_move_id.line_ids.filtered(
            lambda l: l.account_id == self.igtf_account
        )
        self.assertAlmostEqual(sum(igtf_lines.mapped("credit")), 3.48, places=2)
