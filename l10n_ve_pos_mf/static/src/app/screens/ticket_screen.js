import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { ReprintInvoiceButton } from "@l10n_ve_pos_mf/app/components/reprint_invoice_button/reprint_invoice_button";

patch(TicketScreen, {
    components: {
        ...TicketScreen.components,
        ReprintInvoiceButton,
    },
});
