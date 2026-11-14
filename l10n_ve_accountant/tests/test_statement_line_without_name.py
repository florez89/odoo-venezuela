from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "l10n_ve_accountant")
class TestStatementLineWithoutName(TransactionCase):
    """Odoo 18 creates every bank statement line move with name=False (closing a
    PoS session with cash does it too); that must not count as a duplicate name."""

    def test_several_statement_lines_can_be_created(self):
        company = self.env.company
        usd = self.env.ref("base.USD")
        usd.active = True
        if not company.foreign_currency_id:
            company.foreign_currency_id = usd if company.currency_id != usd else self.env.ref("base.VEF")
        company.foreign_currency_id.active = True
        self.env["res.currency.rate"].create(
            {"currency_id": company.foreign_currency_id.id, "company_id": company.id, "rate": 40.0}
        )
        journal = self.env["account.journal"].search(
            [("type", "in", ("cash", "bank")), *self.env["account.journal"]._check_company_domain(company)],
            limit=1,
        )
        # A draft entry without name nor partner is what the duplicate check used to match.
        draft = self.env["account.move"].create({"move_type": "entry", "name": False})
        self.assertFalse(draft.name)
        lines = self.env["account.bank.statement.line"]
        for amount in (10.0, 20.0, 30.0):
            lines |= lines.create(
                {"journal_id": journal.id, "amount": amount, "payment_ref": f"Line {amount}"}
            )
        self.assertEqual(len(lines.move_id), 3)
