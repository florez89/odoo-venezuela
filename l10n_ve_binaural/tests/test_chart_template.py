from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVeBinauralChartTemplate(TransactionCase):
    def test_load_ve_binaural_chart(self):
        """The `ve_binaural` template must ship its own CSV data
        (`<model>-ve_binaural.csv`); otherwise loading fails with
        "External ID not found ... account_activa_account_1122001"."""
        company = self.env["res.company"].create({
            "name": "VE Binaural chart test",
            "country_id": self.env.ref("base.ve").id,
            "currency_id": self.env.ref("base.VES").id,
        })
        self.env["account.chart.template"].try_loading("ve_binaural", company, install_demo=False)
        self.assertEqual(company.chart_template, "ve_binaural")
        self.assertEqual(company.account_sale_tax_id.amount, 16.0)
        receivable = self.env["account.account"].with_company(company).search(
            [("code", "=", "1122001"), ("company_ids", "in", company.id)]
        )
        self.assertTrue(receivable)
        # Invoice lines without a product account need the company defaults.
        # account codes are company dependent: read them in the new company
        company_ctx = company.with_company(company)
        self.assertEqual(company_ctx.income_account_id.code, "5111001")
        self.assertEqual(company_ctx.expense_account_id.code, "7151001")
