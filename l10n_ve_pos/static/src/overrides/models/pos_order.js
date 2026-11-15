import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { floatIsZero, roundDecimals } from "@web/core/utils/numbers";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import {
    formatForeignAmount,
    inverseRate,
    roundForeignAmount,
} from "@l10n_ve_pos/app/utils/foreign_currency";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (this.state === "draft" && typeof this.id !== "number") {
            // Rate in force when the order is created: the order keeps it.
            if (!this.foreign_currency_rate) {
                this.foreign_currency_rate = this.config.foreign_rate || 0;
            }
            // Venezuelan PoS orders are invoiced by default (fiscal document).
            if (!("to_invoice" in vals)) {
                this.to_invoice = true;
            }
        }
    },

    get foreignCurrency() {
        return this.company.foreign_currency_id || false;
    },

    /** Rate shown to the user (e.g. VEF per USD). */
    get_display_rate() {
        return this.foreign_currency_rate || this.config.foreign_rate || 0;
    },

    /** Factor converting an amount of the company currency into the foreign currency. */
    get_conversion_rate() {
        const rate = this.get_display_rate();
        if (rate && rate === this.config.foreign_rate && this.config.foreign_inverse_rate) {
            return this.config.foreign_inverse_rate;
        }
        return inverseRate(rate, this.foreignCurrency);
    },

    localToForeign(amount) {
        return roundForeignAmount(amount * this.get_conversion_rate(), this.foreignCurrency);
    },

    foreignToLocal(amount) {
        const factor = this.get_conversion_rate();
        return factor ? roundDecimals(amount / factor, this.currency.decimal_places) : 0;
    },

    /**
     * Same summary as `taxTotals`, computed with the prices of the lines in the
     * foreign currency (see PosOrderline.get_foreign_unit_price).
     */
    get foreignTaxTotals() {
        const currency = this.foreignCurrency;
        if (!currency) {
            return null;
        }
        const company = this.company;
        const documentSign = this.taxTotals.order_sign;
        const baseLines = this.lines.map((line) =>
            accountTaxHelpers.prepare_base_line_for_taxes_computation(
                line,
                line.prepareBaseLineForTaxesComputationExtraValues({
                    quantity: documentSign * line.qty,
                    price_unit: line.get_foreign_unit_price(),
                    currency_id: currency,
                })
            )
        );
        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, company);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, company);
        const totals = accountTaxHelpers.get_tax_totals_summary(baseLines, currency, company, {});
        totals.order_sign = documentSign;
        return totals;
    },

    get_foreign_total_with_tax() {
        const totals = this.foreignTaxTotals;
        return totals ? totals.order_sign * totals.total_amount_currency : 0;
    },

    get_foreign_total_without_tax() {
        const totals = this.foreignTaxTotals;
        return totals ? totals.order_sign * totals.base_amount_currency : 0;
    },

    get_foreign_total_tax() {
        const totals = this.foreignTaxTotals;
        return totals ? totals.order_sign * totals.tax_amount_currency : 0;
    },

    get_foreign_total_paid() {
        return roundForeignAmount(
            this.payment_ids
                .filter((p) => p.is_done() && !p.is_change)
                .reduce((sum, p) => sum + p.get_foreign_amount(), 0),
            this.foreignCurrency
        );
    },

    get_foreign_due() {
        return roundForeignAmount(
            this.get_foreign_total_with_tax() - this.get_foreign_total_paid(),
            this.foreignCurrency
        );
    },

    get_foreign_change() {
        const total = this.get_foreign_total_with_tax();
        const sign = total < 0 ? -1 : 1;
        return roundForeignAmount(
            Math.max(0, sign * (this.get_foreign_total_paid() - total)),
            this.foreignCurrency
        );
    },

    get_qty_products() {
        return this.lines.reduce((sum, line) => sum + line.qty, 0);
    },

    /** Values of the foreign currency block of the order widgets. */
    getForeignSummary() {
        const currency = this.foreignCurrency;
        if (!currency) {
            return false;
        }
        const tax = this.get_foreign_total_tax();
        return {
            rate: formatForeignAmount(this.get_display_rate(), currency, false),
            total: formatForeignAmount(this.get_foreign_total_with_tax(), currency),
            tax: floatIsZero(tax, currency.decimal_places) ? "" : formatForeignAmount(tax, currency),
            quantity: this.get_qty_products(),
        };
    },

    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        const currency = this.foreignCurrency;
        if (currency) {
            Object.assign(result, {
                foreign_amount_total: this.get_foreign_total_with_tax(),
                foreign_total_without_tax: this.get_foreign_total_without_tax(),
                foreign_amount_tax: this.get_foreign_total_tax(),
                foreign_total_paid: this.get_foreign_total_paid(),
                foreign_amount_total_text: formatForeignAmount(
                    this.get_foreign_total_with_tax(),
                    currency
                ),
                foreign_rate_text: formatForeignAmount(this.get_display_rate(), currency, false),
            });
        }
        return result;
    },

    serialize(options = {}) {
        const data = super.serialize(...arguments);
        if (options.orm && this.foreignCurrency) {
            data.foreign_currency_rate = this.get_display_rate();
            data.foreign_amount_total = this.get_foreign_total_with_tax();
        }
        return data;
    },
});
