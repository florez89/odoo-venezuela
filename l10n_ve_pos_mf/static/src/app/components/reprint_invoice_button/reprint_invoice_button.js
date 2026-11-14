import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

/** Ticket screen button: reprint the fiscal document of the order on the fiscal printer. */
export class ReprintInvoiceButton extends Component {
    static template = "l10n_ve_pos_mf.ReprintInvoiceButton";
    static props = { order: Object };

    setup() {
        this.pos = usePos();
    }

    async onClick() {
        const order = this.props.order;
        const fdm = this.pos.useFiscalMachine();
        if (!fdm || !order.mf_invoice_number) {
            return;
        }
        const amount = order.payment_ids.reduce((sum, payment) => sum + payment.amount, 0);
        await fdm.action({
            action: "reprint",
            data: {
                type: amount >= 0 ? "out_invoice" : "out_refund",
                mf_number: order.mf_invoice_number,
            },
        });
    }
}
