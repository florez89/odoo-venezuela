import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenStatus.prototype, {
    get igtfDetails() {
        return this.props.order.igtfDetails;
    },
    get igtfAmountText() {
        return this.env.utils.formatCurrency(this.igtfDetails.igtf);
    },
    get biIgtfText() {
        return this.env.utils.formatCurrency(this.igtfDetails.base);
    },
    get foreignIgtfText() {
        return this.env.utils.formatForeignCurrency?.(this.igtfDetails.foreignIgtf) || "";
    },
});
