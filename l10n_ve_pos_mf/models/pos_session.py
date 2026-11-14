from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PosSession(models.Model):
    _inherit = "pos.session"

    serial_machine = fields.Char(related="config_id.iface_fiscal_data_module.serial_machine")
    iot_mf = fields.Many2one(related="config_id.iface_fiscal_data_module")
    report_z = fields.Char()

    def set_report_z(self, values):
        self.write({"report_z": int(values["data"]["_dailyClosureCounter"]) + 1})
