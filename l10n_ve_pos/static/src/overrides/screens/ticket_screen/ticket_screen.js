import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { FullRefundButton } from "@l10n_ve_pos/app/components/full_refund/full_refund";

patch(TicketScreen, {
    components: {
        ...TicketScreen.components,
        FullRefundButton,
    },
});
