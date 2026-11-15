import { DebugWidget } from "@point_of_sale/app/debug/debug_widget";
import { patch } from "@web/core/utils/patch";
import { printReportX } from "@l10n_ve_pos_mf/app/fiscal_reports";

patch(DebugWidget.prototype, {
    async fiscalProgramming() {
        const fdm = this.pos.useFiscalMachine();
        if (fdm) {
            await fdm.action({ action: "programacion", data: {} });
        }
    },
    async fiscalReportX() {
        await printReportX(this.pos);
    },
});
