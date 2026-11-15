from odoo import fields, models, api, _


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    code_fiscal_printer = fields.Char(size=2, default="01")

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        return res + [name for name in ("code_fiscal_printer",) if name not in res]
