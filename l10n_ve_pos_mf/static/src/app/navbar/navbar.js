import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { FiscalReportsPopup } from "@l10n_ve_pos_mf/app/components/fiscal_reports_popup/fiscal_reports_popup";
import { testFiscalMachine } from "@l10n_ve_pos_mf/app/fiscal_reports";

patch(Navbar.prototype, {
    async onClickTestFiscalMachine() {
        let connected = false;
        try {
            connected = await testFiscalMachine(this.pos);
        } catch {
            connected = false;
        }
        if (!connected) {
            this.dialog.add(AlertDialog, {
                title: _t("The fiscal machine could not be reached"),
                body: _t("Check that it is turned on and connected to the IoT Box."),
            });
        }
    },
    showFiscalReportsPopup() {
        this.dialog.add(FiscalReportsPopup);
    },
});
