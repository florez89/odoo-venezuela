# -*- coding: utf-8 -*-
from odoo import api, fields, models

class DestajoProducto(models.Model):
    _name = 'destajo.producto'
    _description = 'Producto / Prenda / Modelo a Destajo'
    _order = 'name'

    name = fields.Char(string='Nombre del Producto / Prenda', required=True, index=True)
    code = fields.Char(string='Código / Referencia', index=True)
    description = fields.Text(string='Descripción / Especificaciones')
    active = fields.Boolean(string='Activo', default=True)

    operacion_ids = fields.One2many('destajo.operacion', 'producto_id', string='Operaciones y Tarifas')
    total_operaciones = fields.Integer(string='N° Operaciones', compute='_compute_totales', store=True)
    costo_unitario_total = fields.Float(string='Costo Mano de Obra Total ($ USD)', compute='_compute_totales', store=True, digits=(16, 4))
    
    lote_ids = fields.One2many('destajo.lote', 'producto_id', string='Lotes / Cortes')

    @api.depends('operacion_ids', 'operacion_ids.price_usd', 'operacion_ids.active')
    def _compute_totales(self):
        for prod in self:
            active_ops = prod.operacion_ids.filtered(lambda op: op.active)
            prod.total_operaciones = len(active_ops)
            prod.costo_unitario_total = sum(op.price_usd for op in active_ops)
