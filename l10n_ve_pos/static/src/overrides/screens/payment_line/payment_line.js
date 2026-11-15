import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenPaymentLines.prototype, {
    formatForeignLineAmount(paymentline) {
        return this.env.utils.formatForeignCurrency(paymentline.get_foreign_amount());
    },
});
