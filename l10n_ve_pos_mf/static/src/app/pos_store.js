import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /** DeviceController of the fiscal printer (iot.device of type fiscal_data_module). */
    useFiscalMachine() {
        return this.hardwareProxy.deviceControllers.fiscal_data_module;
    },

    aditionalInfo(order) {
        return [
            `OPERADOR: ${this.get_cashier()?.name || ""}`,
            `PEDIDO: ${order.pos_reference || order.name || ""}`,
        ];
    },

    normalizeProductName(text) {
        if (!text) {
            return "";
        }
        return text
            .normalize("NFKD")
            .replace(/[̀-ͯ]/g, "")
            .replace(/[^\w\s]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    },

    /** Document sent to the fiscal printer for the order. */
    get_data_invoice(order) {
        const invoice = {
            company_id: { name: this.company.name },
            flag_21: this.config.flag_21,
            traditional_line: this.config.traditional_line,
            has_cashbox: this.config.has_cashbox && order.is_paid_with_cash(),
            time: Date.now(),
            info: this.aditionalInfo(order),
            type: order.get_total_with_tax() < 0 ? "out_refund" : "out_invoice",
        };
        const partner = order.get_partner();
        if (partner) {
            invoice.partner_id = {
                vat: `${partner.prefix_vat || ""}${partner.vat || ""}`,
                name: this.normalizeProductName(partner.name),
                address: partner.street || false,
                phone: partner.phone || false,
            };
        }
        if (invoice.type === "out_refund") {
            const refunded = order.lines.find((line) => line.refunded_orderline_id)
                ?.refunded_orderline_id?.order_id;
            if (refunded) {
                invoice.invoice_affected = {
                    number: refunded.mf_invoice_number,
                    serial_machine: refunded.fiscal_machine,
                    date: refunded.date_order,
                };
            }
        }
        // The fiscal printer works in bolivars: the company amounts, or the
        // foreign amounts when the company currency is the dollar.
        const localIsBolivar = this.currency.name !== "USD";
        invoice.invoice_lines = order.lines.map((line) => {
            for (const note of (line.customer_note || "").split("\n").filter(Boolean)) {
                invoice.info.push(note);
            }
            const tax = line.tax_ids?.[0];
            return {
                price_unit: localIsBolivar ? line.get_unit_price() : line.get_foreign_unit_price(),
                discount: line.get_discount(),
                quantity: Math.abs(line.qty),
                name: this.normalizeProductName(line.product_id.display_name),
                code: line.product_id.default_code || false,
                tax: tax ? tax.fiscal_code || 0 : 0,
            };
        });
        invoice.payment_lines = order.payment_ids
            .filter((payment) => !payment.is_change)
            .map((payment) => ({
                payment_method: payment.payment_method_id.code_fiscal_printer,
                amount: localIsBolivar ? payment.get_amount() : payment.get_foreign_amount(),
            }));
        invoice.valid = true;
        return invoice;
    },

    /** Send the document to the fiscal printer and wait for its answer. */
    print_out_invoice(data) {
        const fdm = this.useFiscalMachine();
        if (!fdm) {
            return Promise.reject({
                valid: false,
                message: _t("No fiscal machine is configured"),
            });
        }
        const requestData = { action: `print_${data.type}`, data };
        return new Promise((resolve, reject) => {
            const listener = (answer) => {
                if (answer.request_data?.action !== requestData.action) {
                    return;
                }
                if (answer.status?.status === "connected") {
                    if (answer.value && answer.value.message === "No se ha completado") {
                        return;
                    }
                    fdm.removeListener(listener);
                    resolve(answer);
                } else {
                    fdm.removeListener(listener);
                    reject(answer);
                }
            };
            fdm.addListener(listener);
            fdm.action(requestData)
                .then((response) => {
                    if (!response?.result) {
                        fdm.removeListener(listener);
                        reject({
                            valid: false,
                            message: _t(
                                "Error connecting to the fiscal machine, check if it is turned on or connected to the IoT"
                            ),
                            printer_connection: false,
                        });
                    }
                })
                .catch((error) => {
                    fdm.removeListener(listener);
                    reject({
                        valid: false,
                        message:
                            error?.statusText === "timeout"
                                ? _t("The tax machine did not respond in time")
                                : _t("Error with the tax machine"),
                        printer_connection: false,
                    });
                });
        });
    },

    set_data_from_fiscal_machine(order, data) {
        order.fiscal_machine = data.serial_machine || false;
        order.mf_invoice_number = data.sequence || false;
        order.mf_reportz = data.mf_reportz || false;
    },

    /**
     * Print the order on the fiscal printer.
     * @returns {Promise<{valid: boolean, message: string, printer_connection: boolean}>}
     */
    async pushToMF(order) {
        try {
            const data = this.get_data_invoice(order);
            if (!data.valid) {
                throw { valid: false, message: data.message };
            }
            const { value } = await this.print_out_invoice(data);
            if (!value?.valid) {
                throw { valid: false, message: value?.message, printer_connection: true };
            }
            this.set_data_from_fiscal_machine(order, value);
            return { valid: true, message: "", printer_connection: true };
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("MF error"),
                body: error?.message || error?.status || _t("Internal MF error"),
            });
            return { printer_connection: false, ...error, valid: false };
        }
    },
});
