from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "l10n_ve_iot_mf")
class TestIotMfTours(HttpCase):
    def test_01_fiscal_printer_device_buttons(self):
        """The form of a fiscal printer shows the fiscal printer buttons (view
        widget iot-mf-button) and they send their action to the IoT device."""
        iot_box = self.env["iot.box"].sudo().create(
            {"name": "iotbox-ve-test", "identifier": "01:01:01:01:01:0e", "ip": "1.1.1.1"}
        )
        device = self.env["iot.device"].sudo().create(
            {
                "iot_id": iot_box.id,
                "name": "HKA fiscal printer",
                "identifier": "ve_fiscal_printer",
                "type": "fiscal_data_module",
                "connection": "serial",
            }
        )
        # Build what the first request would otherwise build within the timeout of
        # the tour (statics of the addons, backend bundles).
        self.url_open("/web/static/img/logo.png", timeout=300)
        for bundle_name in ("web.assets_backend", "web.assets_tests"):
            bundle = self.env["ir.qweb"]._get_asset_bundle(bundle_name)
            bundle.js()
            bundle.css()
        self.start_tour(
            "/odoo/iot.device/%d" % device.id, "l10n_ve_iot_mf_fiscal_device_tour", login="admin"
        )
