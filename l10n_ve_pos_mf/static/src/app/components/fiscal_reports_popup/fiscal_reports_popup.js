import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { printReportX, printReportZ } from "@l10n_ve_pos_mf/app/fiscal_reports";

export class FiscalReportsPopup extends Component {
    static template = "l10n_ve_pos_mf.FiscalReportsPopup";
    static components = { Dialog };
    static props = { close: Function };

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
    }

    async run(report) {
        this.ui.block();
        try {
            await report(this.pos);
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("MF error"),
                body: error?.message || _t("Internal MF error"),
            });
        } finally {
            this.ui.unblock();
        }
    }

    reportX() {
        return this.run(printReportX);
    }

    reportZ() {
        return this.run(printReportZ);
    }
}
