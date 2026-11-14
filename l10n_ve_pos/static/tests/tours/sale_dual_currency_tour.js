import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import { mockFiscalPrinter } from "@l10n_ve_pos/../tests/tours/utils/fiscal_printer_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_ve_pos_sale_dual_currency_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            mockFiscalPrinter(),
            ProductScreen.clickDisplayedProduct("VE Taxed Product"),
            ProductScreen.selectedOrderlineHas("VE Taxed Product", "1.00", "116.00"),
            {
                content: "the order line shows its price in the foreign currency",
                trigger: ".orderline.selected .ve-foreign-price:contains('2.90')",
            },
            {
                content: "the order summary shows the rate and the foreign total",
                trigger: ".order-summary .ve-foreign-rate:contains('40')",
            },
            {
                trigger: ".order-summary .ve-foreign-total:contains('2.90')",
            },
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("VE Customer"),
            ProductScreen.clickPayButton(),
            PaymentScreen.isInvoiceButtonChecked(),
            {
                content: "the payment screen shows the foreign total due",
                trigger: ".payment-screen .ve-foreign-due:contains('2.90')",
            },
            PaymentScreen.clickPaymentMethod("Bank USD"),
            {
                content: "a foreign currency payment line shows its foreign amount",
                trigger: ".paymentline.selected .ve-foreign-amount:contains('2.90')",
            },
            // The amount typed on a foreign currency method is in that currency.
            PaymentScreen.clickNumpad("2"),
            {
                content: "2 USD typed: the line is 2 USD (80.00 in the company currency)",
                trigger: ".paymentline.selected .ve-foreign-amount:contains('2.00')",
            },
            PaymentScreen.selectedPaymentlineHas("Bank USD", "80.00"),
            PaymentScreen.remainingIs("36.00"),
            {
                content: "the remaining amount is also shown in the foreign currency",
                trigger: ".payment-screen .ve-foreign-remaining:contains('0.90')",
            },
            PaymentScreen.clickNumpad("."),
            PaymentScreen.clickNumpad("9"),
            {
                content: "2.90 USD typed: exactly the amount due",
                trigger: ".paymentline.selected .ve-foreign-amount:contains('2.90')",
            },
            PaymentScreen.selectedPaymentlineHas("Bank USD", "116.00"),
            PaymentScreen.remainingIs("0.00"),
            PaymentScreen.validateButtonIsHighlighted(true),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            {
                content: "the receipt shows the foreign total",
                trigger: ".pos-receipt .ve-foreign-total:contains('2.90')",
            },
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});
