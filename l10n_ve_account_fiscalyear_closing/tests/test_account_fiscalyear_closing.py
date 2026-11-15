from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "l10n_ve_account_fiscalyear_closing")
class TestVeFiscalYearClosing(TransactionCase):
    """Fiscal year closing with Venezuelan accounts on a USD company whose
    foreign currency is the bolivar (VEF)."""

    # Bolivars per dollar used by each document of the closed year.
    SALE_RATE = 40.0
    PURCHASE_RATE = 50.0

    @classmethod
    def _setup_currencies(cls):
        cls.currency = cls.env.ref("base.USD")
        cls.foreign_currency = cls.env.ref("base.VEF")

    @classmethod
    def _create_rate(cls, date, bs_per_usd):
        values = {
            "name": date,
            "currency_id": cls.foreign_currency.id,
            "company_id": cls.company.id,
        }
        if cls.foreign_currency == cls.env.ref("base.USD"):
            values["inverse_company_rate"] = bs_per_usd
        else:
            values["rate"] = bs_per_usd
        cls.env["res.currency.rate"].create(values)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_currencies()
        (cls.currency | cls.foreign_currency).active = True
        cls.company = cls.env.company
        cls.company.write(
            {
                "currency_id": cls.currency.id,
                "foreign_currency_id": cls.foreign_currency.id,
            }
        )
        cls._create_rate("2025-01-01", cls.SALE_RATE)
        cls._create_rate("2025-07-01", cls.PURCHASE_RATE)

        Account = cls.env["account.account"].with_company(cls.company)
        company_domain = Account._check_company_domain(cls.company)
        # P&L accounts of the Venezuelan chart of accounts
        cls.income_account = Account.search(
            company_domain + [("account_type", "=", "income")], order="code", limit=1
        )
        cls.expense_account = Account.search(
            company_domain + [("account_type", "=", "expense")], order="code", limit=1
        )
        cls.unaffected_account = Account.search(
            company_domain + [("account_type", "=", "equity_unaffected")], limit=1
        )
        # Result account configured on the closing, on purpose not the
        # "current year earnings" account the chart flags as unaffected.
        cls.result_account = Account.create(
            {
                "name": "Resultado del ejercicio (test)",
                "code": "399999",
                "account_type": "equity",
            }
        )
        cls.journal = cls.env["account.journal"].search(
            [
                *cls.env["account.journal"]._check_company_domain(cls.company),
                ("type", "=", "general"),
            ],
            limit=1,
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Cierre"})
        # Venezuelan invoices require a product on every line
        cls.product = cls.env["product.product"].create(
            {"name": "Servicio Cierre", "type": "service", "taxes_id": False, "supplier_taxes_id": False}
        )

        cls.out_invoice = cls._create_posted_invoice(
            "out_invoice", "2025-03-10", cls.income_account, 1000.0
        )
        cls.in_invoice = cls._create_posted_invoice(
            "in_invoice", "2025-08-10", cls.expense_account, 300.0
        )

    @classmethod
    def _create_posted_invoice(cls, move_type, date, account, amount):
        invoice = cls.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": cls.partner.id,
                "invoice_date": date,
                "date": date,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": account.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        invoice.with_context(move_action_post_alert=True).action_post()
        return invoice

    def _create_closing(self, **values):
        return self.env["account.fiscalyear.closing"].create(
            {
                "name": "Cierre 2025",
                "year": 2025,
                "company_id": self.company.id,
                "date_start": "2025-01-01",
                "date_end": "2025-12-31",
                "date_opening": "2026-01-01",
                "check_draft_moves": True,
                "move_config_ids": [
                    Command.create(
                        {
                            "name": "Cierre de cuentas de resultado",
                            "code": "PL",
                            "move_type": "loss_profit",
                            "closing_type_default": "balance",
                            "journal_id": self.journal.id,
                            "date": "2025-12-31",
                            "mapping_ids": [
                                Command.create(
                                    {
                                        "src_accounts": account.code,
                                        "dest_account_id": self.result_account.id,
                                    }
                                )
                                for account in self.income_account | self.expense_account
                            ],
                        }
                    )
                ],
                **values,
            }
        )

    def _year_balances(self, account):
        lines = self.env["account.move.line"].search(
            [
                ("account_id", "=", account.id),
                ("parent_state", "=", "posted"),
                ("date", ">=", "2025-01-01"),
                ("date", "<=", "2025-12-31"),
            ]
        )
        return sum(lines.mapped("balance")), self._foreign_balance(lines)

    @staticmethod
    def _foreign_balance(lines):
        # foreign debit/credit: the stored foreign_balance of vendor bill lines
        # created from code is left empty by l10n_ve_accountant
        return sum(lines.mapped("foreign_debit")) - sum(lines.mapped("foreign_credit"))

    def test_setup_has_profit(self):
        """The year to close has posted invoices on the Venezuelan P&L accounts."""
        self.assertTrue(self.income_account and self.expense_account)
        self.assertNotEqual(self.income_account, self.expense_account)
        self.assertEqual(self.out_invoice.state, "posted")
        self.assertEqual(self.in_invoice.state, "posted")
        balance, foreign_balance = self._year_balances(self.income_account)
        self.assertAlmostEqual(balance, -1000.0, places=2)
        self.assertAlmostEqual(
            foreign_balance, -1000.0 * self._foreign_factor(self.SALE_RATE), places=2
        )

    def _foreign_factor(self, bs_per_usd):
        """Foreign amount of one unit of company currency."""
        if self.foreign_currency == self.env.ref("base.USD"):
            return 1 / bs_per_usd
        return bs_per_usd

    def test_closing_zeroes_pl_accounts_into_result_account(self):
        closing = self._create_closing()
        closing.button_calculate()
        self.assertEqual(closing.state, "calculated")
        self.assertTrue(closing.move_ids)
        self.assertTrue(all(move.state == "draft" for move in closing.move_ids))
        for move in closing.move_ids:
            self.assertEqual(move.journal_id, self.journal)
            self.assertEqual(move.date, fields.Date.to_date("2025-12-31"))
            self.assertEqual(move.closing_type, "loss_profit")
            self.assertAlmostEqual(sum(move.line_ids.mapped("debit")), sum(move.line_ids.mapped("credit")), places=2)
            self.assertAlmostEqual(self._foreign_balance(move.line_ids), 0.0, places=2)

        closing.button_post()
        self.assertEqual(closing.state, "posted")
        self.assertTrue(all(move.state == "posted" for move in closing.move_ids))

        for account in self.income_account | self.expense_account:
            balance, foreign_balance = self._year_balances(account)
            self.assertAlmostEqual(balance, 0.0, places=2, msg=account.code)
            self.assertAlmostEqual(foreign_balance, 0.0, places=2, msg=account.code)

        result_lines = closing.move_ids.line_ids.filtered(
            lambda line: line.account_id == self.result_account
        )
        # profit of 1000 - 300 lands as a credit on the configured result account
        self.assertAlmostEqual(sum(result_lines.mapped("balance")), -700.0, places=2)
        self.assertAlmostEqual(
            self._foreign_balance(result_lines),
            -1000.0 * self._foreign_factor(self.SALE_RATE)
            + 300.0 * self._foreign_factor(self.PURCHASE_RATE),
            places=2,
        )
        self.assertFalse(
            closing.move_ids.line_ids.filtered(
                lambda line: line.account_id == self.unaffected_account
            )
        )

    def test_cancel_and_back_to_draft(self):
        closing = self._create_closing()
        closing.button_calculate()
        closing.button_post()
        moves = closing.move_ids
        self.assertTrue(moves)

        closing.button_cancel()
        self.assertEqual(closing.state, "cancelled")
        self.assertFalse(closing.move_ids)
        self.assertFalse(moves.exists())
        for account in self.income_account | self.expense_account:
            self.assertNotAlmostEqual(self._year_balances(account)[0], 0.0, places=2)

        closing.button_recover()
        self.assertEqual(closing.state, "draft")
        self.assertFalse(closing.calculation_date)
        closing.button_calculate()
        self.assertEqual(closing.state, "calculated")
        self.assertTrue(closing.move_ids)

    def test_recalculate_replaces_moves(self):
        closing = self._create_closing()
        closing.button_calculate()
        first_moves = closing.move_ids
        closing.button_recalculate()
        self.assertFalse(first_moves.exists())
        self.assertEqual(len(closing.move_ids), len(first_moves))

    def test_draft_moves_block_the_closing(self):
        draft = self.out_invoice.copy({"invoice_date": "2025-05-05", "date": "2025-05-05"})
        self.assertEqual(draft.state, "draft")
        closing = self._create_closing()
        with self.assertRaises(ValidationError):
            closing.button_calculate()
        closing.check_draft_moves = False
        closing.button_calculate()
        self.assertEqual(closing.state, "calculated")

    def test_load_accounts_maps_pl_accounts(self):
        closing = self._create_closing()
        config = closing.move_config_ids
        config.l_map = True
        result = config.onchange_l_map()
        mappings = [command[2] for command in result["value"]["mapping_ids"]]
        codes = {values["src_accounts"] for values in mappings}
        self.assertIn(self.income_account.code, codes)
        self.assertIn(self.expense_account.code, codes)
        self.assertNotIn(self.result_account.code, codes)
        self.assertEqual({values["dest_account_id"] for values in mappings}, {self.unaffected_account.id})

        config.l_map = False
        self.assertEqual(config.onchange_l_map(), {"value": {"mapping_ids": [Command.clear()]}})

    def test_template_load_accounts_maps_pl_accounts(self):
        template = self.env["account.fiscalyear.closing.template"].create(
            {
                "name": "Plantilla de cierre",
                "company_id": self.company.id,
                "chart_template": self.company.chart_template,
                "move_config_ids": [
                    Command.create(
                        {
                            "name": "Cierre de cuentas de resultado",
                            "code": "PL",
                            "move_type": "loss_profit",
                            "journal_id": self.journal.id,
                        }
                    )
                ],
            }
        )
        config = template.move_config_ids
        config.l_map = True
        result = config.inchange_l_map()
        mappings = [command[2] for command in result["value"]["mapping_ids"]]
        codes = {values["src_accounts"] for values in mappings}
        self.assertIn(self.income_account.code, codes)
        self.assertIn(self.expense_account.code, codes)
        self.assertEqual({values["dest_account"] for values in mappings}, {self.unaffected_account.code})


@tagged("post_install", "-at_install", "l10n_ve_account_fiscalyear_closing")
class TestVeFiscalYearClosingBolivarCompany(TestVeFiscalYearClosing):
    """Same closing on a bolivar (VES) company whose foreign currency is USD."""

    # run the tests of the parent class with these currencies
    allow_inherited_tests_method = True

    @classmethod
    def _setup_currencies(cls):
        cls.currency = cls.env.ref("base.VES")
        cls.foreign_currency = cls.env.ref("base.USD")
