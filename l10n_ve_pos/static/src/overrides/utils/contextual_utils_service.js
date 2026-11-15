import { contextualUtilsService } from "@point_of_sale/app/utils/contextual_utils_service";
import { patch } from "@web/core/utils/patch";
import { formatForeignAmount } from "@l10n_ve_pos/app/utils/foreign_currency";

patch(contextualUtilsService, {
    start(env, { pos }) {
        super.start(...arguments);
        env.utils.formatForeignCurrency = (value, hasSymbol = true) =>
            formatForeignAmount(value, pos.foreignCurrency, hasSymbol);
    },
});
