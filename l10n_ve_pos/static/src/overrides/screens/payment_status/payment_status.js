import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenStatus.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },
    get foreignRemainingText() {
        const due = this.props.order.get_foreign_due();
        return this.env.utils.formatForeignCurrency(due > 0 ? due : 0);
    },
    get foreignChangeText() {
        return this.env.utils.formatForeignCurrency(this.props.order.get_foreign_change());
    },
});
