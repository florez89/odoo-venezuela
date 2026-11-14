import { HardwareProxy } from "@point_of_sale/app/hardware_proxy/hardware_proxy_service";
import { patch } from "@web/core/utils/patch";

patch(HardwareProxy.prototype, {
    /** The cash drawer is connected to the fiscal printer. */
    async openCashbox() {
        const fdm = this.deviceControllers?.fiscal_data_module;
        if (fdm && this.pos.config.has_cashbox) {
            return fdm.action({ action: "logger", data: "0" });
        }
        return super.openCashbox(...arguments);
    },
});
