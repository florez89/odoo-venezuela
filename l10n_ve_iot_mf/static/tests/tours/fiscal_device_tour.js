import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_ve_iot_mf_fiscal_device_tour", {
    steps: () => [
        {
            content: "the fiscal printer buttons are shown",
            trigger: ".o_form_view .o_form_statusbar button:contains('Generate Report X')",
            run: () => {
                // Stand for the IoT Box: every action is accepted.
                const { IoTLongpolling } = odoo.loader.modules.get("@iot/iot_longpolling");
                window.__veIotActions = [];
                IoTLongpolling.prototype.action = async function (iotIp, identifier, data) {
                    window.__veIotActions.push(data);
                    return { result: true };
                };
                IoTLongpolling.prototype.addListener = function () {};
                IoTLongpolling.prototype.removeListener = function () {};
            },
        },
        {
            trigger: ".o_form_view .o_form_statusbar button:contains('Test')",
        },
        {
            content: "print the X report",
            trigger: ".o_form_view .o_form_statusbar button:contains('Generate Report X')",
            run: "click",
        },
        {
            content: "the IoT Box accepted the action",
            trigger: ".o_notification:contains('Successfully sent to printer!')",
            run: () => {
                const actions = window.__veIotActions.map((data) => data.action);
                if (!actions.includes("report_x")) {
                    throw new Error(`Expected a report_x action, got ${JSON.stringify(actions)}`);
                }
            },
        },
    ],
});
