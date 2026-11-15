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
        # Odoo 18 keeps the default income/expense accounts on the product category
        category = self.env.ref("product.product_category_all", raise_if_not_found=False)
        if category:
            category = category.with_company(company)
            self.assertEqual(category.property_account_income_categ_id.code, "5111001")
            self.assertEqual(category.property_account_expense_categ_id.code, "7151001")
