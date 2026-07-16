# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class L10nVePrestacionesLedger(models.Model):
    _name = 'l10n_ve.prestaciones.ledger'
    _description = 'Libro Auxiliar de Prestaciones'
    _order = 'date desc'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade')
    payslip_id = fields.Many2one('hr.payslip', string='Recibo de Nomina', ondelete='set null')
    date = fields.Date(string='Mes', required=True)
    salary_integral_daily = fields.Float(string='Salario Integral Diario', digits=(16, 2), default=0.0)
    days_garantia = fields.Float(string='Dias Garantia', default=0.0)
    amount_garantia = fields.Float(string='Monto Garantia', digits=(16, 2), default=0.0)
    days_adicionales = fields.Float(string='Dias Adicionales', default=0.0)
    amount_adicionales = fields.Float(string='Monto Adicionales', digits=(16, 2), default=0.0)
    previous_balance = fields.Float(string='Saldo Anterior', digits=(16, 2), default=0.0)
    accumulated_balance = fields.Float(string='Acumulado Prestaciones', digits=(16, 2), default=0.0)
    bcv_rate_id = fields.Many2one('l10n_ve.prestaciones.rate', string='Tasa BCV Prestaciones')
    bcv_interest_rate = fields.Float(string='Tasa Interes BCV (%)', digits=(16, 2), default=0.0)
    amount_interest = fields.Float(string='Interes del Mes', digits=(16, 2), default=0.0)
    previous_accumulated_interest = fields.Float(string='Intereses Acum. Anterior', digits=(16, 2), default=0.0)
    accumulated_interest = fields.Float(string='Acumulado Intereses', digits=(16, 2), default=0.0)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Publicado')
    ], string='Estado', default='draft', required=True)

    _sql_constraints = [
        ('employee_date_unique', 'unique(employee_id, date)', 'Ya existe un registro en el libro auxiliar para este empleado en este mes.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'date' in vals and vals['date']:
                d = fields.Date.from_string(vals['date'])
                vals['date'] = d.replace(day=1)
        return super(L10nVePrestacionesLedger, self).create(vals_list)

    def write(self, vals):
        if 'date' in vals and vals['date']:
            d = fields.Date.from_string(vals['date'])
            vals['date'] = d.replace(day=1)
        return super(L10nVePrestacionesLedger, self).write(vals)
