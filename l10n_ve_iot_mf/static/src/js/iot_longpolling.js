/** @odoo-module **/

import { IoTLongpolling } from "@iot/iot_longpolling";
import { patch } from "@web/core/utils/patch";

patch(IoTLongpolling.prototype, {
    async setup() {
        await super.setup(...arguments);
        // Fiscal printers can take long to answer (reports, long documents).
        this.POLL_TIMEOUT = 6000000;
        this.ACTION_TIMEOUT = 1600000;
    },
});
