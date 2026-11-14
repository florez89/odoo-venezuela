import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /** The foreign currency of the company (USD for a VEF company and vice versa). */
    get foreignCurrency() {
        return this.company?.foreign_currency_id || false;
    },
});
