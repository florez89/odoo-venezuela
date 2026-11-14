from odoo import api, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    @api.model
    def _load_pos_data_domain(self, data):
        """Load the foreign currency of the company too: the PoS shows and takes
        amounts in it."""
        domain = super()._load_pos_data_domain(data)
        config = data["pos.config"]["data"][0]
        company = self.env["res.company"].browse(config["company_id"])
        if not company.foreign_currency_id:
            return domain
        currency_ids = {company.currency_id.id, config["currency_id"], company.foreign_currency_id.id}
        return [("id", "in", list(currency_ids))]
