/* global posmodel */

export const FAKE_FISCAL_SERIAL = "Z1A1234567";
export const FAKE_FISCAL_NUMBER = "00000123";

/**
 * Stands for the IoT DeviceController of a fiscal printer (l10n_ve_pos_mf):
 * every print request is answered as printed with a fixed fiscal number.
 */
export class FakeFiscalPrinter {
    constructor() {
        this.listeners = [];
        this.requests = [];
    }
    action(requestData) {
        this.requests.push(requestData);
        setTimeout(() => {
            for (const listener of [...this.listeners]) {
                listener({
                    request_data: requestData,
                    status: { status: "connected" },
                    value: {
                        valid: true,
                        serial_machine: FAKE_FISCAL_SERIAL,
                        sequence: FAKE_FISCAL_NUMBER,
                    },
                });
            }
        });
        return Promise.resolve({ result: true });
    }
    addListener(callback) {
        this.listeners.push(callback);
    }
    removeListener(callback) {
        this.listeners = callback ? this.listeners.filter((l) => l !== callback) : [];
    }
}

/**
 * Replace the fiscal printer of the PoS, if it has one (l10n_ve_pos_mf
 * installed: every PoS then needs one), by a FakeFiscalPrinter.
 */
export function mockFiscalPrinter() {
    return [
        {
            content: "replace the fiscal printer (if any) by a fake one",
            trigger: ".pos .pos-content",
            run: () => {
                const controllers = posmodel.hardwareProxy.deviceControllers;
                if (controllers?.fiscal_data_module) {
                    controllers.fiscal_data_module = new FakeFiscalPrinter();
                }
            },
        },
    ];
}
