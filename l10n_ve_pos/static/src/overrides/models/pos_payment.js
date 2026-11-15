import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";
import { floatIsZero } from "@web/core/utils/numbers";
import { roundForeignAmount } from "@l10n_ve_pos/app/utils/foreign_currency";

patch(PosPayment.prototype, {
    get_foreign_amount() {
        return this.foreign_amount || 0;
    },

    /** Amount in the company currency: the foreign amount follows with the order rate. */
    set_amount(value) {
        super.set_amount(...arguments);
        const order = this.pos_order_id;
        if (order?.foreignCurrency) {
            this.foreign_amount = order.localToForeign(this.amount);
        }
    },

    /**
     * Amount in the foreign currency (methods with is_foreign_currency). Paying
     * exactly the foreign amount due pays exactly the amount due, without the
     * rounding of the conversion.
     */
    set_foreign_amount(value) {
        const order = this.pos_order_id;
        const currency = order.foreignCurrency;
        const foreignAmount = roundForeignAmount(parseFloat(value) || 0, currency);
        const foreignDue = order.get_foreign_due() + (this.is_done() ? this.get_foreign_amount() : 0);
        const localDue = order.get_due() + (this.is_done() ? this.get_amount() : 0);
        const amount = floatIsZero(foreignAmount - foreignDue, currency.decimal_places)
            ? localDue
            : order.foreignToLocal(foreignAmount);
        this.set_amount(amount);
        this.foreign_amount = foreignAmount;
    },

    serialize(options = {}) {
        const data = super.serialize(...arguments);
        if (options.orm && this.pos_order_id?.foreignCurrency) {
            data.foreign_rate = this.pos_order_id.get_display_rate();
            data.foreign_amount = this.get_foreign_amount();
        }
        return data;
    },
});
