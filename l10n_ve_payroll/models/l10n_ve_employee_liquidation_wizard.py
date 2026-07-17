# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class L10nVeEmployeeLiquidationWizard(models.TransientModel):
    _name = 'l10n_ve.employee.liquidation.wizard'
    _description = 'Asistente para Preparar Liquidación'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    exit_date = fields.Date(string='Fecha de Egreso', required=True, default=fields.Date.context_today)
    exit_reason = fields.Selection([
        ('justified_dismissal', 'Despido Justificado'),
        ('unjustified_dismissal', 'Despido Injustificado / Retiro Justificado'),
        ('resignation', 'Renuncia'),
        ('common_agreement', 'Mutuo Acuerdo'),
        ('retirement', 'Jubilación'),
        ('death', 'Fallecimiento')
    ], string='Motivo de Egreso', required=True, default='resignation')

    def action_confirm(self):
        self.ensure_one()
        if not self.employee_id.contract_date_start:
            raise UserError(_("El empleado debe tener una fecha de ingreso configurada para poder preparar su liquidación."))
            
        self.employee_id.write({
            'l10n_ve_liquidation_state': 'to_liquidate',
            'l10n_ve_exit_date': self.exit_date,
            'l10n_ve_exit_reason': self.exit_reason,
        })

