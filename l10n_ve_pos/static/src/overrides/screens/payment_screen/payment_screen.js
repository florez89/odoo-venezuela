import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    shouldDownloadInvoice() {
        // Venezuelan invoices are printed by the fiscal printer.
        return false;
    },

    /** The amount typed on a foreign currency method is in that currency. */
    updateSelectedPaymentline(amount = false) {
        const line = this.selectedPaymentLine;
        if (!line || !line.payment_method_id.is_foreign_currency || !this.pos.foreignCurrency) {
            return super.updateSelectedPaymentline(...arguments);
        }
        if (amount === false) {
            if (this.numberBuffer.get() === null) {
                amount = null;
            } else if (this.numberBuffer.get() === "") {
                amount = 0;
            } else {
                amount = this.numberBuffer.getFloat();
            }
        }
        const paymentTerminal = line.payment_method_id.payment_terminal;
        if (paymentTerminal && !["pending", "retry"].includes(line.get_payment_status())) {
            return;
        }
        if (amount === null) {
            this.deletePaymentLine(line.uuid);
        } else {
            line.set_foreign_amount(amount);
        }
    },

    async _isOrderValid(isForceValidate) {
        const order = this.currentOrder;
        if (
            order &&
            order.get_total_with_tax() !== 0 &&
            order.payment_ids.some((line) => !line.is_change && !line.get_amount())
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Empty Paymentline"),
                body: _t("You can't validate with empty payment lines"),
            });
            return false;
        }
        return super._isOrderValid(...arguments);
    },

    get refundedOrder() {
        return this.currentOrder?.lines.find((line) => line.refunded_orderline_id)
            ?.refunded_orderline_id?.order_id;
    },

    /** Show the payments of the refunded order (method and foreign amount). */
    async showPaymentsOrigin() {
        const refundedOrder = this.refundedOrder;
        if (!refundedOrder || typeof refundedOrder.id !== "number") {
            return;
        }
        const payments = await this.pos.data.call("pos.order", "get_payments_order_refund", [
            [refundedOrder.id],
        ]);
        await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Payments"),
            list: payments.map((payment) => ({
                id: payment.id,
                label: `${payment.payment_method_id[1]} ${
                    payment.display_name
                } / ${this.env.utils.formatForeignCurrency(payment.foreign_amount)}`,
                isSelected: false,
                item: payment,
            })),
        });
    },
});
