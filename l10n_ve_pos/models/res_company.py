from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pos_show_free_qty = fields.Boolean()
    pos_show_just_products_with_available_qty = fields.Boolean()
    pos_move_to_draft = fields.Boolean()
    pos_search_cne = fields.Boolean()
    pos_unreconcile_moves = fields.Boolean()
    pos_show_free_qty_on_warehouse = fields.Boolean()

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        extra = ["foreign_currency_id"]
        if "taxpayer_type" in self._fields:  # l10n_ve_tax_payer
            extra.append("taxpayer_type")
        return res + [name for name in extra if name not in res]
