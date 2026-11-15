from odoo.tests import tagged

from .common import VePosHttpCommon


@tagged("post_install", "-at_install", "l10n_ve_pos")
class TestVePosTours(VePosHttpCommon):
    def test_01_sale_dual_currency_foreign_payment(self):
        """A sale with the VE sale tax shows the foreign (USD) amounts, is paid
        typing the amount in USD, is saved with its foreign amounts and its
        session closes with them."""
        self.start_ve_pos_tour("l10n_ve_pos_sale_dual_currency_tour")

        order = self.last_order()
        self.assertTrue(order, "The tour must create an order")
        self.assertIn(order.state, ("paid", "done", "invoiced"))
        self.assertAlmostEqual(order.amount_total, 116.0, places=2)
        self.assertAlmostEqual(order.foreign_currency_rate, self.FOREIGN_RATE, places=2)
        self.assertAlmostEqual(order.foreign_amount_total, 2.90, places=2)
        self.assertAlmostEqual(order.lines.foreign_price, 2.50, places=2)

        usd_payment = order.payment_ids
        self.assertEqual(usd_payment.payment_method_id, self.bank_usd_method)
        self.assertAlmostEqual(usd_payment.foreign_amount, 2.90, places=2)
        self.assertAlmostEqual(usd_payment.amount, 116.0, places=2)
        self.assertAlmostEqual(usd_payment.foreign_rate, self.FOREIGN_RATE, places=2)

        invoice = order.account_move
        self.assertTrue(invoice, "VE PoS orders are invoiced by default")
        self.assertEqual(invoice.state, "posted")
        self.assertAlmostEqual(invoice.foreign_rate, self.FOREIGN_RATE, places=2)
        self.assertAlmostEqual(invoice.foreign_inverse_rate, 1 / self.FOREIGN_RATE, places=6)
        self.assertAlmostEqual(invoice.amount_total, 116.0, places=2)

        # Closing the session posts its journal entry with the foreign amounts.
        session = order.session_id
        session.post_closing_cash_details(session.cash_register_balance_end)
        result = session.close_session_from_ui()
        self.assertTrue(result.get("successful"), result)
        self.assertEqual(session.state, "closed")
        self.assertEqual(session.move_id.state, "posted")
        self.assertAlmostEqual(session.move_id.foreign_rate, self.FOREIGN_RATE, places=2)

        # The sale details report of the session adds the foreign amounts.
        details = self.env["report.point_of_sale.report_saledetails"].get_sale_details(
            session_ids=session.ids
        )
        self.assertEqual(details["foreign_currency"], self.usd)
        self.assertAlmostEqual(details["foreign_total_paid"], 2.90, places=2)
        html = self.env["ir.actions.report"]._render_qweb_html(
            "point_of_sale.sale_details_report",
            [],
            data={"date_start": False, "date_stop": False, "config_ids": [], "session_ids": session.ids},
        )[0]
        self.assertIn(b"2.90", html)
