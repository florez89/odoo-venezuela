import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { printReportX, printReportZ } from "@l10n_ve_pos_mf/app/fiscal_reports";

patch(ClosePosPopup.prototype, {
    async runFiscalReport(report) {
        try {
            await report(this.pos);
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("MF error"),
                body: error?.message || _t("Internal MF error"),
            });
        }
    },
    generate_report_x() {
        return this.runFiscalReport(printReportX);
    },
    generate_report_z() {
        return this.runFiscalReport(printReportZ);
    },
});
