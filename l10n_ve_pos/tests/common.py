from odoo import Command, fields
from odoo.tests import HttpCase


class VePosHttpCommon(HttpCase):
    """Venezuelan PoS on the main company: company currency VEF (or whatever the
    database uses), foreign currency USD at 40 VEF per USD, a product with the
    sale tax of the chart and three payment methods (cash and bank in the
    company currency, bank typed in the foreign currency)."""

    FOREIGN_RATE = 40.0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.company = env.company
        cls.usd = env.ref("base.USD")
        cls.usd.active = True
        if cls.company.currency_id == cls.usd:
            cls.skipTest(cls, "The Venezuelan PoS tours expect a company currency other than USD.")
        cls.company.foreign_currency_id = cls.usd
        env["res.currency.rate"].search(
            [("currency_id", "=", cls.usd.id), ("company_id", "in", (cls.company.id, False))]
        ).unlink()
        env["res.currency.rate"].create(
            {
                "name": fields.Date.today(),
                "currency_id": cls.usd.id,
                "company_id": cls.company.id,
                "inverse_company_rate": cls.FOREIGN_RATE,
            }
        )

        cls.pos_admin = env.ref("base.user_admin")
        cls.pos_admin.groups_id += env.ref("point_of_sale.group_pos_manager")

        Account = env["account.account"]
        if not cls.company.account_default_pos_receivable_account_id:
            cls.company.account_default_pos_receivable_account_id = Account.create(
                {
                    "code": "X1012VE",
                    "name": "PoS Receivable - Test",
                    "account_type": "asset_receivable",
                    "reconcile": True,
                }
            )
        cls.outstanding_account = Account.create(
            {
                "code": "X1013VE",
                "name": "PoS Outstanding - Test",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )

        Journal = env["account.journal"]
        cls.cash_journal = Journal.create({"name": "Cash VEF Test", "type": "cash", "code": "VCSH"})
        cls.bank_usd_journal = Journal.create({"name": "Bank USD Test", "type": "bank", "code": "VBKD"})
        cls.bank_journal = Journal.create({"name": "Bank VEF Test", "type": "bank", "code": "VBNK"})

        PaymentMethod = env["pos.payment.method"]
        cls.cash_method = PaymentMethod.create(
            {"name": "Cash VEF", "journal_id": cls.cash_journal.id}
        )
        cls.bank_usd_method = PaymentMethod.create(
            {
                "name": "Bank USD",
                "journal_id": cls.bank_usd_journal.id,
                "outstanding_account_id": cls.outstanding_account.id,
                "is_foreign_currency": True,
            }
        )
        cls.bank_method = PaymentMethod.create(
            {
                "name": "Bank VEF",
                "journal_id": cls.bank_journal.id,
                "outstanding_account_id": cls.outstanding_account.id,
            }
        )

        cls.sale_tax = cls.company.account_sale_tax_id or env["account.tax"].create(
            {"name": "IVA 16% Test", "amount": 16.0, "type_tax_use": "sale"}
        )
        cls.product = env["product.product"].create(
            {
                "name": "VE Taxed Product",
                "type": "consu",
                "list_price": 100.0,
                "available_in_pos": True,
                "taxes_id": [Command.set(cls.sale_tax.ids)],
            }
        )
        cls.partner = env["res.partner"].create(
            {
                "name": "VE Customer",
                "prefix_vat": "V",
                "vat": "12345678",
                "street": "Av. Principal",
                "country_id": env.ref("base.ve").id,
                "phone": "04121234567",
            }
        )

        env["pos.config"].search([("company_id", "=", cls.company.id)]).filtered(
            lambda c: not c.current_session_id
        ).active = False
        cls.pos_config = env["pos.config"].create(
            {
                "name": "VE Shop",
                "iface_tax_included": "total",
                "payment_method_ids": [
                    Command.set((cls.cash_method + cls.bank_usd_method + cls.bank_method).ids)
                ],
            }
        )

        # With l10n_ve_pos_mf every PoS needs an IoT fiscal printer to open; the
        # tours replace it by a fake one (static/tests/tours/utils).
        cls.fiscal_device = False
        if "iface_fiscal_data_module" in cls.pos_config._fields:
            iot_box = env["iot.box"].sudo().create(
                {"name": "iotbox-ve-test", "identifier": "01:01:01:01:01:0f", "ip": "1.1.1.1"}
            )
            cls.fiscal_device = env["iot.device"].sudo().create(
                {
                    "iot_id": iot_box.id,
                    "name": "Fiscal printer",
                    "identifier": "ve_fiscal_printer",
                    "type": "fiscal_data_module",
                    "connection": "serial",
                    "serial_machine": "Z1A1234567",
                }
            )
            cls.pos_config.write(
                {"is_posbox": True, "iface_fiscal_data_module": cls.fiscal_device.id}
            )

    def start_ve_pos_tour(self, tour_name, **kwargs):
        # The first static file request of the server process lists the static
        # folders of every addon (http.Application.statics); on slow addons paths
        # it outlasts the timeout of a tour step, so do it before the tour.
        self.url_open("/web/static/img/logo.png", timeout=300)
        # Same for the first build of the PoS asset bundles (the tour waits 60 s
        # for the PoS to be ready).
        for bundle_name in ("point_of_sale.assets_prod", "web.assets_tests"):
            bundle = self.env["ir.qweb"]._get_asset_bundle(bundle_name)
            bundle.js()
            bundle.css()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.pos_config.id, tour_name, login="admin", **kwargs
        )

    def last_order(self):
        return self.env["pos.order"].search(
            [("config_id", "=", self.pos_config.id)], order="id desc", limit=1
        )
