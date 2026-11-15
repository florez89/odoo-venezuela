import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    /** IGTF of this payment ({ base, igtf, foreignIgtf }), see PosOrder._computeIgtf. */
    get igtfDetails() {
        return this.pos_order_id?.igtfDetails.byPayment[this.uuid] || false;
    },

    serialize(options = {}) {
        const data = super.serialize(...arguments);
        if (options.orm) {
            const details = this.igtfDetails;
            data.include_igtf = Boolean(details && details.igtf);
            data.igtf_amount = details ? details.igtf : 0;
            data.foreign_igtf_amount = details ? details.foreignIgtf : 0;
        }
        return data;
    },
});
