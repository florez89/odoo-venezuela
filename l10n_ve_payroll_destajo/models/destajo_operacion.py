# -*- coding: utf-8 -*-
from odoo import fields, models

class DestajoOperacion(models.Model):
    _name = 'destajo.operacion'
    _description = 'Operación / Tarea de Producción'
    _order = 'producto_id, sequence, id'

    producto_id = fields.Many2one('destajo.producto', string='Producto / Prenda', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    name = fields.Char(string='Nombre de la Operación / Tarea', required=True)
    price_usd = fields.Float(
        string='Tarifa ($ USD)', 
        required=True, 
        default=0.0, 
        digits=(16, 4),
        help='Tarifa en dólares pagada por cada pieza elaborada de esta operación.'
    )
    active = fields.Boolean(string='Activo', default=True)
