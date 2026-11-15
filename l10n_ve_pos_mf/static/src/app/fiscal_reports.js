import { _t } from "@web/core/l10n/translation";

/**
 * Fiscal printer reports shared by the navbar dialog, the closing popup and the
 * debug widget. `pos` is the PosStore.
 */
export async function printReportX(pos) {
    const fdm = pos.useFiscalMachine();
    if (!fdm) {
        return;
    }
    await fdm.action({ action: "report_x", data: {} });
}

/** Print the Z report and save its number on the account moves and the session. */
export async function printReportZ(pos) {
    const fdm = pos.useFiscalMachine();
    if (!fdm) {
        return;
    }
    const value = await new Promise((resolve, reject) => {
        const listener = (answer) => {
            if (answer.request_data && answer.request_data.action !== "report_z") {
                return;
            }
            fdm.removeListener(listener);
            if (answer.status?.status === "connected" && answer.value?.valid !== false) {
                resolve(answer.value);
            } else {
                reject(answer.value || { message: _t("The Z report could not be printed") });
            }
        };
        fdm.addListener(listener);
        fdm.action({ action: "report_z", data: {} }).then((response) => {
            if (!response?.result) {
                fdm.removeListener(listener);
                reject({ message: _t("No connection to the fiscal machine") });
            }
        }, reject);
    });
    await pos.data.call("account.move", "report_z", [[], pos.config.serial_machine, value]);
    await pos.data.call("pos.session", "set_report_z", [[pos.session.id], value]);
    return value;
}

export async function testFiscalMachine(pos) {
    const fdm = pos.useFiscalMachine();
    const response = fdm && (await fdm.action({ action: "test", data: true }));
    return Boolean(response?.result);
}
