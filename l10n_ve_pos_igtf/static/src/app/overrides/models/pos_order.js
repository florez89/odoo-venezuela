import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { floatIsZero, roundDecimals } from "@web/core/utils/numbers";

patch(PosOrder.prototype, {
    get igtfRate() {
        return (this.config.igtf_percentage || 0) / 100;
    },

    /**
     * IGTF of the order: each payment of a method with apply_igtf pays a part of
     * the base (invoice total) plus the IGTF of that part. The payments are taken
     * in order; the other payments pay base only. Invoiced orders only.
     *
     * @param {number} baseTotal signed invoice total (without IGTF)
     * @returns {{ igtf: number, foreignIgtf: number, base: number, byPayment: Object }}
     */
    _computeIgtf(baseTotal) {
        const result = { igtf: 0, foreignIgtf: 0, base: 0, byPayment: {} };
        const rate = this.igtfRate;
        if (!this.to_invoice || !rate || !baseTotal) {
            return result;
        }
        const decimals = this.currency.decimal_places;
        const sign = baseTotal < 0 ? -1 : 1;
        let remainingBase = sign * baseTotal;
        for (const payment of this.payment_ids) {
            if (payment.is_change) {
                continue;
            }
            const amount = sign * payment.get_amount();
            if (!payment.payment_method_id.apply_igtf) {
                remainingBase -= amount;
                continue;
            }
            const base = Math.max(0, Math.min(amount / (1 + rate), remainingBase));
            const igtf = roundDecimals(base * rate, decimals);
            remainingBase -= base;
            const foreignIgtf = this.localToForeign ? this.localToForeign(igtf) : 0;
            result.byPayment[payment.uuid] = {
                base: sign * base,
                igtf: sign * igtf,
                foreignIgtf: sign * foreignIgtf,
            };
            result.igtf += sign * igtf;
            result.foreignIgtf += sign * foreignIgtf;
            result.base += sign * base;
        }
        result.igtf = roundDecimals(result.igtf, decimals);
        result.base = roundDecimals(result.base, decimals);
        return result;
    },

    get igtfDetails() {
        const totals = super.taxTotals;
        return this._computeIgtf(totals.order_sign * totals.order_total);
    },

    /** The customer pays the invoice total plus the IGTF. */
    get taxTotals() {
        const totals = super.taxTotals;
        const { igtf } = this._computeIgtf(totals.order_sign * totals.order_total);
        if (!igtf) {
            return totals;
        }
        const signedIgtf = totals.order_sign * igtf;
        totals.igtf_amount = signedIgtf;
        totals.order_total += signedIgtf;
        totals.order_remaining += signedIgtf;
        totals.order_has_zero_remaining = floatIsZero(
            totals.order_remaining + totals.order_rounding,
            this.currency.decimal_places
        );
        return totals;
    },

    get_igtf_amount() {
        return this.igtfDetails.igtf;
    },

    get_foreign_igtf_amount() {
        return this.igtfDetails.foreignIgtf;
    },

    get_bi_igtf() {
        return this.igtfDetails.base;
    },

    get_foreign_total_with_tax() {
        return super.get_foreign_total_with_tax(...arguments) + this.get_foreign_igtf_amount();
    },

    /** A new payment of an IGTF method pays the remaining base plus its IGTF. */
    getDefaultAmountDueToPayIn(paymentMethod) {
        const amount = super.getDefaultAmountDueToPayIn(...arguments);
        if (!paymentMethod.apply_igtf || !this.to_invoice || !this.igtfRate) {
            return amount;
        }
        return roundDecimals(amount * (1 + this.igtfRate), this.currency.decimal_places);
    },

    serialize(options = {}) {
        const data = super.serialize(...arguments);
        if (options.orm) {
            const details = this.igtfDetails;
            data.igtf_amount = details.igtf;
            data.bi_igtf = details.base;
            // amount_total is the invoice total: without the IGTF.
            if (details.igtf && typeof data.amount_total === "number") {
                data.amount_total = roundDecimals(
                    data.amount_total - details.igtf,
                    this.currency.decimal_places
                );
            }
        }
        return data;
    },
});
