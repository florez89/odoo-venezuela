# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class L10nVePrestacionesRate(models.Model):
    _name = 'l10n_ve.prestaciones.rate'
    _description = 'Tasas de Interes BCV para Prestaciones'
    _order = 'date desc'

    date = fields.Date(string='Mes de Vigencia', required=True)
    rate = fields.Float(string='Tasa de Interes (%)', required=True, digits=(16, 2))
    name = fields.Char(string='Descripcion', compute='_compute_name', store=True)

    _sql_constraints = [
        ('date_unique', 'unique(date)', 'Ya existe una tasa registrada para este mes.')
    ]

    @api.depends('date')
    def _compute_name(self):
        for rec in self:
            if rec.date:
                months = {
                    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                }
                rec.name = f"{months[rec.date.month]} {rec.date.year}"
            else:
                rec.name = ""

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'date' in vals and vals['date']:
                d = fields.Date.from_string(vals['date'])
                vals['date'] = d.replace(day=1)
        return super(L10nVePrestacionesRate, self).create(vals_list)

    def write(self, vals):
        if 'date' in vals and vals['date']:
            d = fields.Date.from_string(vals['date'])
            vals['date'] = d.replace(day=1)
        return super(L10nVePrestacionesRate, self).write(vals)
