import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { roundDecimals } from "@web/core/utils/numbers";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { formatForeignAmount } from "@l10n_ve_pos/app/utils/foreign_currency";

patch(PosOrderline.prototype, {
    setup(vals) {
        super.setup(...arguments);
        // A refund keeps the foreign price (and so the rate) of the refunded line.
        if (!this.foreign_price && this.refunded_orderline_id?.foreign_price) {
            this.foreign_price = this.refunded_orderline_id.foreign_price;
        }
    },

    get foreignCurrency() {
        return this.order_id?.foreignCurrency || false;
    },

    get foreignPriceDigits() {
        const dp = this.models["decimal.precision"].find(
            (dp) => dp.name === "Foreign Product Price"
        );
        return dp ? dp.digits : this.foreignCurrency?.decimal_places ?? 2;
    },

    /**
     * Unit price in the foreign currency: the price of the refunded line for a
     * refund, else the unit price converted with the rate of the order.
     */
    get_foreign_unit_price() {
        if (this.refunded_orderline_id && this.foreign_price) {
            return this.foreign_price;
        }
        const factor = this.order_id?.get_conversion_rate() || 0;
        return roundDecimals(this.get_unit_price() * factor, this.foreignPriceDigits);
    },

    get_all_foreign_prices(qty = this.get_quantity()) {
        const currency = this.foreignCurrency;
        const baseLine = accountTaxHelpers.prepare_base_line_for_taxes_computation(
            this,
            this.prepareBaseLineForTaxesComputationExtraValues({
                quantity: qty,
                tax_ids: this.tax_ids || this.get_product().taxes_id,
                price_unit: this.get_foreign_unit_price(),
                currency_id: currency,
            })
        );
        accountTaxHelpers.add_tax_details_in_base_line(baseLine, this.company);
        accountTaxHelpers.round_base_lines_tax_details([baseLine], this.company);
        return {
            priceWithTax: baseLine.tax_details.total_included_currency,
            priceWithoutTax: baseLine.tax_details.total_excluded_currency,
        };
    },

    get_display_foreign_price() {
        const prices = this.get_all_foreign_prices();
        return this.config.iface_tax_included === "total"
            ? prices.priceWithTax
            : prices.priceWithoutTax;
    },

    get_unit_display_foreign_price() {
        const prices = this.get_all_foreign_prices(1);
        return this.config.iface_tax_included === "total"
            ? prices.priceWithTax
            : prices.priceWithoutTax;
    },

    /** (E) exempt or (G) general rate, as printed on Venezuelan fiscal documents. */
    get_aliquot_type() {
        const taxes = this.tax_ids?.length ? this.tax_ids : this.get_product()?.taxes_id || [];
        if (!taxes.length || taxes[0].amount === 0) {
            return "(E)";
        }
        return "(G)";
    },

    getDisplayData() {
        const data = super.getDisplayData(...arguments);
        const currency = this.foreignCurrency;
        if (!currency) {
            return data;
        }
        return {
            ...data,
            foreignPrice:
                this.get_discount_str() === "100"
                    ? ""
                    : formatForeignAmount(this.get_display_foreign_price(), currency),
            foreignUnitPrice: formatForeignAmount(this.get_unit_display_foreign_price(), currency),
            aliquotType: this.get_aliquot_type(),
        };
    },

    serialize(options = {}) {
        const data = super.serialize(...arguments);
        if (options.orm && this.foreignCurrency) {
            data.foreign_price = this.get_foreign_unit_price();
        }
        return data;
    },
});
