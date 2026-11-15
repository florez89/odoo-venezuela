from odoo.tests import TransactionCase, tagged
from odoo.tools import sql


@tagged("post_install", "-at_install")
class TestSqlConstraints(TransactionCase):
    """Odoo 19 ignores `_sql_constraints`; the models.Constraint declarations
    must exist in the database."""

    def test_constraints_exist(self):
        expected = {
            "economic_activity": ("code_uniq", "aliquot_mayor_cero"),
            "economic_branch": ("name_uniq",),
            "account_withholding_type": ("unique_name", "unique_value"),
            "payment_concept_line": ("unique_code",),
        }
        for table, names in expected.items():
            for name in names:
                with self.subTest(table=table, constraint=name):
                    self.assertTrue(sql.constraint_definition(self.env.cr, table, f"{table}_{name}"))
