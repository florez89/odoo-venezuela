import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    /**
     * Quantity and price can only be changed by the users of the VE PoS groups
     * (rights loaded with the session, see pos.session._load_pos_data).
     */
    getNumpadButtons() {
        const buttons = super.getNumpadButtons();
        const session = this.pos.session;
        for (const button of buttons) {
            if (button.value === "quantity" && !session._l10n_ve_can_change_qty) {
                button.disabled = true;
            }
            if (button.value === "price" && !session._l10n_ve_can_change_price) {
                button.disabled = true;
            }
        }
        return buttons;
    },

    /** Company setting: hide the storable products without stock. */
    get productsToDisplay() {
        const list = super.productsToDisplay;
        if (!this.pos.config.pos_show_just_products_with_available_qty) {
            return list;
        }
        return list.filter((product) => !product.is_storable || product.qty_available > 0);
    },
});
