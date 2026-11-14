import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    /**
     * The order is printed on the fiscal printer before it is saved: it keeps the
     * fiscal number and the serial of the machine. When the printer fails the
     * order stays on the payment screen.
     */
    async _finalizeValidation() {
        const order = this.currentOrder;
        if (this.pos.useFiscalMachine() && !order.mf_invoice_number) {
            this.env.services.ui.block();
            let response;
            try {
                response = await this.pos.pushToMF(order);
            } finally {
                this.env.services.ui.unblock();
            }
            if (!response.valid) {
                return;
            }
        }
        return super._finalizeValidation(...arguments);
    },
});
