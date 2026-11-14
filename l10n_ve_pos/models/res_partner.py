from odoo import models, fields, api, _
from ...tools import binaural_cne_query
from odoo.exceptions import MissingError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_default_name_by_vat_param(self, prefix_vat, vat):
        name, flag = binaural_cne_query.get_default_name_by_vat(self, prefix_vat, vat)
        if not flag:
            raise MissingError(
                _(
                    "Error to connect with CNE, please check your internet connection or try again later"
                )
            )

        return name

    @api.model
    def _load_pos_data_fields(self, config_id):
        """The PoS shows the document type (V, J, E...) with the VAT. Partners are
        created and edited in the PoS with the backend form (point_of_sale.
        res_partner_action_edit_pos), which already has the VE fields."""
        res = super()._load_pos_data_fields(config_id)
        return res + [name for name in ("prefix_vat",) if name not in res]
