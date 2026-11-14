from odoo.tests import tagged

from odoo.addons.l10n_ve_pos.tests.common import VePosHttpCommon


@tagged("post_install", "-at_install", "l10n_ve_pos_mf")
class TestVePosMfTours(VePosHttpCommon):
    def test_01_fiscal_printer_order_flow(self):
        """Validating an order prints it on the (mocked) fiscal printer and saves
        the fiscal number and machine serial on the order and its invoice."""
        self.assertTrue(self.fiscal_device, "The common setup gives the PoS a fiscal printer")
        self.start_ve_pos_tour("l10n_ve_pos_mf_fiscal_order_tour")

        order = self.last_order()
        self.assertTrue(order, "The tour must create an order")
        self.assertIn(order.state, ("paid", "done", "invoiced"))
        self.assertEqual(order.mf_invoice_number, "00000123")
        self.assertEqual(order.fiscal_machine, "Z1A1234567")
        invoice = order.account_move
        self.assertTrue(invoice)
        self.assertEqual(invoice.mf_invoice_number, "00000123")
        self.assertEqual(invoice.mf_serial, "Z1A1234567")
        self.assertEqual(invoice.iot_mf, self.fiscal_device)
