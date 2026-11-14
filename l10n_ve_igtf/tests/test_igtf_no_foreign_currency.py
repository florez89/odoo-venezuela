from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("igtf", "-at_install", "post_install")
class TestIGTFWithoutForeignCurrency(TransactionCase):
    """A company without a foreign currency charges no IGTF, but every consumer
    of the tax totals (views, report, amount to pay) still reads the IGTF block."""

    def test_tax_totals_carry_an_empty_igtf_block(self):
        company = self.env.company
        company.foreign_currency_id = False
        partner = self.env["res.partner"].create({"name": "No foreign currency customer"})
        product = self.env["product.product"].create(
            {"name": "IGTF neutral product", "type": "service", "taxes_id": [Command.clear()]}
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "currency_id": company.currency_id.id,
                "invoice_line_ids": [
                    Command.create({"product_id": product.id, "quantity": 1, "price_unit": 100})
                ],
            }
        )

        igtf = invoice.tax_totals["igtf"]
        self.assertFalse(igtf["apply_igtf"])
        self.assertFalse(igtf["is_igtf_suggested"])
        self.assertEqual(igtf["igtf_amount"], 0.0)
        self.assertEqual(igtf["igtf_base_amount"], 0.0)
        self.assertEqual(invoice.amount_to_pay_igtf, 0.0)
