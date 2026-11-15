import { formatFloat, roundDecimals } from "@web/core/utils/numbers";

/**
 * Format an amount of the foreign currency of the company with the symbol and
 * position of that currency (a res.currency record of the PoS data).
 */
export function formatForeignAmount(value, currency, hasSymbol = true) {
    if (!currency) {
        return "";
    }
    const amount = formatFloat(value || 0, { digits: [69, currency.decimal_places] });
    if (!hasSymbol) {
        return amount;
    }
    return currency.position === "after"
        ? `${amount} ${currency.symbol || ""}`
        : `${currency.symbol || ""} ${amount}`;
}

export function roundForeignAmount(value, currency) {
    return roundDecimals(value || 0, currency ? currency.decimal_places : 2);
}

/**
 * Factor that converts an amount in the company currency into the foreign
 * currency, from the rate shown to the user: same rule as
 * res.currency.rate.compute_inverse_rate (l10n_ve_rate).
 */
export function inverseRate(rate, foreignCurrency) {
    if (!rate) {
        return 0;
    }
    return foreignCurrency?.name === "USD" ? 1 / rate : rate;
}
