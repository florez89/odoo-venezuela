import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class AccountFiscalyearClosingConfig(models.Model):
    _inherit = "account.fiscalyear.closing.config"

    l_map = fields.Boolean(string="Load Accounts")

    @api.onchange("l_map")
    def onchange_l_map(self):
        if not self.l_map:
            return {"value": {"mapping_ids": [(5, 0, 0)]}}
        company = self.fyc_id.company_id or self.env.company
        Account = self.env["account.account"].sudo().with_company(company)
        company_domain = Account._check_company_domain(company)
        accounts = Account.search(
            company_domain
            + [
                (
                    "account_type",
                    "in",
                    [
                        "income",
                        "expense",
                        "income_other",
                        "expense_depreciation",
                        "expense_direct_cost",
                    ],
                ),
            ]
        )
        # the destination is always the current year earnings account
        config_a = Account.search(
            company_domain + [("account_type", "=", "equity_unaffected")],
            limit=1,
        )
        maps = [
            (
                0,
                0,
                {
                    "name": account.name,
                    "src_accounts": account.code,
                    "dest_account_id": config_a.id,
                    "fyc_config_id": self.id,
                },
            )
            for account in accounts
            if account.code
        ]
        if maps:
            return {"value": {"mapping_ids": maps}}

    def move_prepare(self, move_lines, rate=0):
        self.ensure_one()
        description = self.name
        journal_id = self.journal_id.id
        return {
            "ref": description,
            "date": self.date,
            "fyc_id": self.fyc_id.id,
            "closing_type": self.move_type,
            "journal_id": journal_id,
            "line_ids": [(0, 0, m) for m in move_lines],
            "foreign_rate": rate,  # Aqui va la informacion la tasa de las lineas
        }

    def _mapping_move_lines_get(self, src, account_map):
        move_lines = []
        dest_totals = {}
        # Add balance/unreconciled move lines
        # for account_map in self.mapping_ids:
        rate = 1

        dest = account_map.dest_account_id
        dest_totals.setdefault(dest, 0)
        # aqui filtrar si viene src usar solo esa
        company = self.fyc_id.company_id
        Account = self.env["account.account"].with_company(company)
        company_domain = Account._check_company_domain(company)
        if not src:
            src_accounts = Account.search(
                company_domain + [("code", "=ilike", account_map.src_accounts)],
                order="code ASC",
            )
        else:
            src_accounts = Account.sudo().search(
                company_domain + [("code", "=ilike", src)]
            )
        for account in src_accounts:
            closing_type = self.closing_type_get(account)
            balance = False
            if closing_type == "balance":
                # Get all lines
                lines = account_map.account_lines_get(account)

                balance, move_line, rate = account_map.move_line_prepare(account, lines)
                if move_line:
                    move_lines.append(move_line)
            elif closing_type == "unreconciled":
                continue
            else:
                # Account type has unsupported closing method
                continue
            if dest and balance:
                dest_totals[dest] -= balance
        # Add destination move lines, if any
        for account_map in self.mapping_ids.filtered("dest_account_id"):
            dest = account_map.dest_account_id
            balance = dest_totals.get(dest, 0)
            if not balance:
                continue
            dest_totals[dest] = 0
            move_line = account_map.dest_move_line_prepare(dest, balance)
            if move_line:
                move_lines.append(move_line)
        return move_lines, rate


class AccountFiscalyearClosing(models.Model):
    _inherit = "account.fiscalyear.closing"

    def draft_moves_check(self):
        for closing in self:
            draft_moves = self.env["account.move"].search(
                [
                    ("company_id", "=", closing.company_id.id),
                    ("state", "=", "draft"),
                    ("date", ">=", closing.date_start),
                    ("date", "<=", closing.date_end),
                ]
            )
            if draft_moves:
                msg = _("Se encontraron uno o más movimientos sin asentar: \n")
                for move in draft_moves:
                    msg += "ID: %s, Date: %s, Number: %s, Ref: %s\n" % (
                        move.id,
                        move.date,
                        move.name,
                        move.ref,
                    )
                raise ValidationError(msg)
        return True

    def _moves_remove(self):
        # l10n_ve_accountant's button_draft handles one move at a time, so the
        # posted moves go back to draft one by one before the generic removal.
        for move in self.move_ids.filtered(lambda move: move.state == "posted"):
            move.button_draft()
        return super()._moves_remove()

    def button_post(self):
        for closing in self:
            closing.move_ids.action_post()
        return super().button_post()

    def calculate(self):
        """Close every mapped account into the result account of its mapping.

        Each source account gets its own move so that the move rate converts
        the account balance into its foreign balance, zeroing both.
        """
        for closing in self:
            # Perform checks, raise exception if check fails
            if closing.check_draft_moves:
                closing.draft_moves_check()

            for config in closing.move_config_ids.filtered("enabled"):
                closing._create_closing_moves(config, closing._get_balances(config))

        return True

    def _get_default_result_account(self):
        """Current year earnings account, used by mappings without destination."""
        self.ensure_one()
        Account = self.env["account.account"].sudo().with_company(self.company_id)
        return Account.search(
            Account._check_company_domain(self.company_id)
            + [("account_type", "=", "equity_unaffected")],
            limit=1,
        )

    def _get_balances(self, config):
        """Return [(account, result account, balance, foreign balance)] of the
        accounts mapped by `config` over the closed period."""
        self.ensure_one()
        Account = self.env["account.account"].with_company(self.company_id)
        company_domain = Account._check_company_domain(self.company_id)
        default_dest = self._get_default_result_account()
        dest_by_account = {}
        for mapping in config.mapping_ids:
            src_accounts = Account.search(
                company_domain + [("code", "=ilike", mapping.src_accounts)],
                order="code ASC",
            )
            for account in src_accounts:
                dest_by_account.setdefault(
                    account, mapping.dest_account_id or default_dest
                )
        if not dest_by_account:
            return []

        domain = [
            ("company_id", "=", self.company_id.id),
            ("account_id", "in", [account.id for account in dest_by_account]),
            ("date", ">=", self.date_start),
            ("date", "<=", self.date_end),
            ("move_id.state", "!=", "cancel"),
        ]
        # foreign debit/credit rather than foreign_balance: the stored
        # foreign_balance of some invoice lines is left empty by
        # l10n_ve_accountant while their foreign debit/credit are right.
        groups = self.env["account.move.line"]._read_group(
            domain,
            groupby=["account_id"],
            aggregates=["balance:sum", "foreign_debit:sum", "foreign_credit:sum"],
        )
        return [
            (account, dest_by_account[account], balance, foreign_debit - foreign_credit)
            for account, balance, foreign_debit, foreign_credit in sorted(
                groups, key=lambda group: group[0].code or ""
            )
        ]

    def _create_closing_moves(self, config, balances):
        self.ensure_one()
        currency = self.company_id.currency_id
        foreign_currency = self.company_id.foreign_currency_id
        is_usd = foreign_currency == self.env.ref("base.USD", raise_if_not_found=False)
        vals = []

        for account, dest_account, balance, foreign_balance in balances:
            if currency.is_zero(balance):
                continue
            if not dest_account:
                raise ValidationError(
                    _(
                        "There is no result account to close the account %(account)s.",
                        account=account.display_name,
                    )
                )
            # Factor that turns the closed balance into its foreign balance.
            # The shown rate follows res.currency.rate.compute_rate: inverse
            # company rate for USD, company rate for any other currency.
            inverse_rate = abs(foreign_balance / balance)
            if is_usd:
                rate = 1 / inverse_rate if inverse_rate else 0.0
            else:
                rate = inverse_rate

            vals.append(
                {
                    "ref": config.name,
                    "date": config.date,
                    "fyc_id": self.id,
                    "closing_type": config.move_type,
                    "journal_id": config.journal_id.id,
                    "foreign_currency_id": foreign_currency.id,
                    "manually_set_rate": True,
                    "foreign_rate": rate,
                    "foreign_inverse_rate": inverse_rate,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "account_id": account.id,
                                "balance": -balance,
                                "name": config.name,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "account_id": dest_account.id,
                                "balance": balance,
                                "name": _("Result"),
                            },
                        ),
                    ],
                }
            )
        return self.env["account.move"].create(vals)


class AccountFiscalyearClosingMapping(models.Model):
    _inherit = "account.fiscalyear.closing.mapping"

    def move_line_prepare(self, account, account_lines, partner_id=False):
        self.ensure_one()
        move_line = {}
        balance = 0
        precision = self.env["decimal.precision"].precision_get("Account")
        description = self.name or account.name
        date = self.fyc_config_id.fyc_id.date_end
        rate = 1
        bsd_id = self.env.ref("base.VEF").id
        if self.fyc_config_id.move_type == "opening":
            date = self.fyc_config_id.fyc_id.date_opening
        if account_lines:
            debits = sum(account_lines.mapped("debit"))
            credits = sum(account_lines.mapped("credit"))
            foreign_debits = sum(account_lines.mapped("foreign_debit"))
            foreign_credits = sum(account_lines.mapped("foreign_credit"))

            balance = debits - credits
            foreign_balance = foreign_debits - foreign_credits
            # balance = sum(account_lines.mapped("debit")) - sum(account_lines.mapped("credit"))

            # foreign_balance = sum(account_lines.mapped("foreign_debit")) - sum(
            #     account_lines.mapped("foreign_credit")
            # )
            foreign_currency = account_lines[0].foreign_currency_id
            if not float_is_zero(balance, precision_digits=precision):
                rate = (
                    foreign_balance / balance
                    if balance > foreign_balance
                    else balance / foreign_balance
                )
                # for line in account_lines:
                # _logger.warning("NO ENTIENDO")
                #
                # line.move_id.write(
                #     {
                #         "manually_set_rate": True,
                #         "foreign_inverse_rate": rate
                #         if bsd_id == foreign_currency.id
                #         else 1 / rate,
                #         "foreign_rate": rate,
                #     }
                # )
                move_line = {
                    "account_id": account.id,
                    "debit": balance < 0 and -balance,
                    "credit": balance > 0 and balance,
                    "name": description,
                    "date": date,
                    "partner_id": partner_id,
                    "foreign_rate": rate,
                    "foreign_inverse_rate": (rate if bsd_id == foreign_currency.id else 1 / rate),
                }
            else:
                balance = 0
        return balance, move_line, abs(rate)

    def account_lines_get(self, account):
        self.ensure_one()
        start = self.fyc_config_id.fyc_id.date_start
        end = self.fyc_config_id.fyc_id.date_end
        company_id = self.fyc_config_id.fyc_id.company_id.id
        domain = [
            ("company_id", "=", company_id),
            # ("account_id", "=", account.id),
            ("date", ">=", start),
            ("date", "<=", end),
            ("move_id.state", "!=", "cancel"),
        ]
        return self.env["account.move.line"].read_group(
            domain=domain,
            fields=[
                "debit",
                "credit",
                "foreign_debit",
                "foreign_credit",
                "account_id",
            ],
            groupby=["account_id"],
        )

    def account_partners_get(self, account):
        self.ensure_one()
        start = self.fyc_config_id.fyc_id.date_start
        end = self.fyc_config_id.fyc_id.date_end
        company_id = self.fyc_config_id.fyc_id.company_id.id
        return self.env["account.move.line"].read_group(
            [
                ("company_id", "=", company_id),
                ("account_id", "=", account.id),
                ("date", ">=", start),
                ("date", "<=", end),
            ],
            ["partner_id", "credit", "debit"],
            ["partner_id"],
        )
