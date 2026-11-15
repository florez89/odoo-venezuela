import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import { mockFiscalPrinter } from "@l10n_ve_pos/../tests/tours/utils/fiscal_printer_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_ve_pos_igtf_payment_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            mockFiscalPrinter(),
            ProductScreen.clickDisplayedProduct("VE Taxed Product"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("VE Customer"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isInvoiceButtonChecked(),
            // The IGTF method pays the remaining base plus 3% IGTF.
            PaymentScreen.clickPaymentMethod("USD IGTF"),
            {
                content: "the payment line shows its IGTF",
                trigger: ".paymentlines .ve-igtf-amount:contains('3.48')",
            },
            PaymentScreen.selectedPaymentlineHas("USD IGTF", "119.48"),
            PaymentScreen.remainingIs("0.00"),
            {
                content: "the payment status shows the IGTF of the order",
                trigger: ".payment-screen .ve-igtf-total:contains('3.48')",
            },
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});
