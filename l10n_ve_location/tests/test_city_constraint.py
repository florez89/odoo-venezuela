from odoo.tests import TransactionCase, tagged
from odoo.tools import sql


@tagged("post_install", "-at_install")
class TestCityConstraint(TransactionCase):

    def test_city_name_unique_constraint_exists(self):
        self.assertTrue(sql.constraint_definition(self.env.cr, "res_country_city", "res_country_city_name_uniq"))
