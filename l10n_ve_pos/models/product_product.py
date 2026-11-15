from odoo import api, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        return res + [name for name in ("free_qty", "qty_available") if name not in res]

    def _load_pos_data(self, data):
        """Quantities of the stock the PoS sells from: the source location of its
        operation type."""
        config = self.env["pos.config"].browse(data["pos.config"]["data"][0]["id"])
        location = config.picking_type_id.default_location_src_id
        if location:
            self = self.with_context(location=location.id)
        res = super()._load_pos_data(data)
        if self.env.company.pos_show_just_products_with_available_qty:
            res["data"] = sorted(
                res["data"], key=lambda p: p.get("qty_available", 0.0), reverse=True
            )
        return res
