from odoo import models, fields

class MoveActionPostAlertWizard(models.TransientModel):
    _name = 'move.action.post.alert.wizard'
    _description = 'Move Action Post Alert'

    move_id = fields.Many2one('account.move')
    is_foreign_rate_outdated = fields.Boolean(related='move_id.is_foreign_rate_outdated')
    foreign_rate_date = fields.Date(related='move_id.foreign_rate_date')
    foreign_rate_age_days = fields.Integer(related='move_id.foreign_rate_age_days')
    is_customer_invoice = fields.Boolean(compute='_compute_is_customer_invoice')

    def _compute_is_customer_invoice(self):
        for wizard in self:
            wizard.is_customer_invoice = wizard.move_id.move_type in ('out_invoice', 'out_refund')
    
    def action_confirm(self):
        self.move_id.with_context(move_action_post_alert=True).action_post()
        return {'type': 'ir.actions.client',
                'tag': 'reload',}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

