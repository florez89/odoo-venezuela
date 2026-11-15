from odoo import api, models


class IotDevice(models.Model):
    _inherit = "iot.device"

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        return res + [name for name in ("flag_21", "traditional_line") if name not in res]
