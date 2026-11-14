import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },
    /** Stock of the PoS source location (company setting "show free quantity"). */
    get showFreeQty() {
        return this.pos.config.pos_show_free_qty && this.props.product?.is_storable;
    },
    get qtyAvailable() {
        return this.env.utils.formatProductQty(this.props.product?.qty_available ?? 0, false);
    },
});
