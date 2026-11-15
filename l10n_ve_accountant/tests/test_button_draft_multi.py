from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "l10n_ve_accountant")
class TestButtonDraftSeveralMoves(TransactionCase):
    """Resetting several posted moves at once (e.g. cancelling a fiscal year
    closing) must work, and only vendor bills get the price-change flag."""

    def test_reset_several_moves_to_draft_at_once(self):
        company = self.env.company
        journal = self.env["account.journal"].search(
            [("type", "=", "general"), *self.env["account.journal"]._check_company_domain(company)],
            limit=1,
        )
        accounts = self.env["account.account"].search(
            [*self.env["account.account"]._check_company_domain(company), ("deprecated", "=", False)],
            limit=2,
        )
        moves = self.env["account.move"].create([
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "line_ids": [
                    Command.create({"account_id": accounts[0].id, "debit": amount}),
                    Command.create({"account_id": accounts[1].id, "credit": amount}),
                ],
            }
            for amount in (10.0, 20.0)
        ])
        moves.action_post()

        moves.button_draft()

        self.assertEqual(set(moves.mapped("state")), {"draft"})
        self.assertFalse(any(moves.mapped("is_reset_to_draft_for_price_change")))
