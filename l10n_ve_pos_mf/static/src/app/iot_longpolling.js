import { IoTLongpolling } from "@iot/iot_longpolling";
import { patch } from "@web/core/utils/patch";

patch(IoTLongpolling.prototype, {
    async setup() {
        await super.setup(...arguments);
        // Fiscal printers can take long to print a document.
        this.POLL_TIMEOUT = 100000;
        this.ACTION_TIMEOUT = 100000;
    },
});
