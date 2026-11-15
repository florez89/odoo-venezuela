# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged

from ..hooks import create_journal_sequences


@tagged("post_install", "-at_install")
class TestJournalSequenceHook(TransactionCase):

    def test_existing_journals_have_sequence(self):
        journals = self.env["account.journal"].with_context(active_test=False).search([])
        self.assertTrue(journals)
        self.assertFalse(journals.filtered(lambda journal: not journal.sequence_id))

    def test_hook_is_idempotent(self):
        before = self.env["ir.sequence"].search_count([])
        create_journal_sequences(self.env)
        self.assertEqual(self.env["ir.sequence"].search_count([]), before)

    def test_new_journal_gets_sequences(self):
        journal = self.env["account.journal"].create({
            "name": "Hook Sales", "code": "HKS", "type": "sale", "refund_sequence": True,
        })
        self.assertEqual(journal.sequence_id.prefix, "HKS/%(range_year)s/")
        self.assertEqual(journal.refund_sequence_id.prefix, "RHKS/%(range_year)s/")
