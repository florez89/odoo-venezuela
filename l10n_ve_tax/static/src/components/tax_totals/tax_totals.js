/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { TaxTotalsComponent } from "@account/components/tax_totals/tax_totals";
import { toRaw } from "@odoo/owl";

/**
 * Read-only tax totals expressed in the foreign currency of the company.
 *
 * The python summary (account.tax._get_tax_totals_summary) carries the full foreign summary
 * under the `foreign_tax_totals` key, with the same structure as the Odoo summary.
 */
export class TaxForeignTotalsComponent extends TaxTotalsComponent {
    static template = "l10n_ve_tax.TaxForeignTotalsField";
    static props = {
        ...standardFieldProps,
    };

    get readonly() {
        return true;
    }

    formatData(props) {
        const totals = toRaw(props.record.data[this.props.name]);
        if (!totals || !totals.foreign_tax_totals) {
            this.totals = null;
            return;
        }
        this.totals = JSON.parse(JSON.stringify(totals.foreign_tax_totals));
    }
}

export const taxForeignTotalsComponent = {
    component: TaxForeignTotalsComponent,
};

registry.category("fields").add("account-tax-foreign-totals-field", taxForeignTotalsComponent);
