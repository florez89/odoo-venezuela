import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/** Ticket screen button: set the whole refundable quantity of every line to refund. */
export class FullRefundButton extends Component {
    static template = "l10n_ve_pos.FullRefundButton";
    static props = {
        order: { type: Object, optional: true },
        ticketScreen: Object,
    };

    setup() {
        this.numberBuffer = useService("number_buffer");
    }

    click() {
        this.numberBuffer.reset();
        const order = this.props.order;
        if (!order) {
            return;
        }
        for (const line of order.lines) {
            const toRefundDetail = this.props.ticketScreen.getToRefundDetail(line);
            // When already linked to an order, do not modify the to refund quantity.
            if (toRefundDetail.destination_order_uuid) {
                continue;
            }
            const refundableQty = line.qty - line.refunded_qty;
            if (refundableQty > 0) {
                toRefundDetail.qty = refundableQty;
            }
        }
    }
}
