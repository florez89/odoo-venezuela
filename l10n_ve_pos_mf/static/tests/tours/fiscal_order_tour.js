/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import { mockFiscalPrinter } from "@l10n_ve_pos/../tests/tours/utils/fiscal_printer_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_ve_pos_mf_fiscal_order_tour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            mockFiscalPrinter(),
            ProductScreen.clickDisplayedProduct("VE Taxed Product"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("VE Customer"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash VEF"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
            {
                content: "the receipt screen shows the fiscal number",
                trigger: ".receipt-screen .ve-mf-invoice-number:contains('00000123')",
            },
            {
                content: "the fiscal printer received one invoice of the order",
                trigger: "body",
                run: () => {
                    const printer = posmodel.hardwareProxy.deviceControllers.fiscal_data_module;
                    const prints = printer.requests.filter((r) => r.action === "print_out_invoice");
                    if (prints.length !== 1) {
                        throw new Error(`Expected 1 fiscal print, got ${prints.length}`);
                    }
                    const data = prints[0].data;
                    if (
                        data.partner_id.vat !== "V12345678" ||
                        data.invoice_lines.length !== 1 ||
                        data.invoice_lines[0].price_unit !== 100 ||
                        data.payment_lines[0].amount !== 116
                    ) {
                        throw new Error(`Unexpected fiscal data ${JSON.stringify(data)}`);
                    }
                },
            },
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});
