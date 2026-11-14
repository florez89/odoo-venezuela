import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenPaymentLines.prototype, {
    formatIgtfAmount(paymentline) {
        const details = paymentline.igtfDetails;
        const igtf = this.env.utils.formatCurrency(details.igtf);
        const foreign = this.env.utils.formatForeignCurrency?.(details.foreignIgtf);
        return foreign ? igtf + " / " + foreign : igtf;
    },
});
