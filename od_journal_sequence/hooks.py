# -*- coding: utf-8 -*-

from .models.account_journal import prepare_journal_sequence_vals


def create_journal_sequences(env):
    """Give every existing journal its sequences before the ORM adds the
    NOT NULL constraint of the new required `sequence_id` column.

    Runs as a pre-init hook: the columns are created here and filled through
    SQL because the fields are not registered yet; journal data is read with
    the ORM (the name is a translated jsonb column).
    """
    cr = env.cr
    cr.execute("""
        ALTER TABLE account_journal
            ADD COLUMN IF NOT EXISTS sequence_id int4,
            ADD COLUMN IF NOT EXISTS refund_sequence_id int4
    """)
    cr.execute("SELECT id FROM account_journal WHERE sequence_id IS NULL")
    journal_ids = [row[0] for row in cr.fetchall()]
    journals = env["account.journal"].with_context(active_test=False).browse(journal_ids)
    Sequence = env["ir.sequence"].sudo()
    for journal in journals:
        journal_vals = {
            "code": journal.code,
            "name": journal.name,
            "company_id": journal.company_id.id,
        }
        sequence = Sequence.create(prepare_journal_sequence_vals(env, journal_vals))
        refund_sequence = Sequence
        if journal.type in ("sale", "purchase") and journal.refund_sequence:
            refund_sequence = Sequence.create(prepare_journal_sequence_vals(env, journal_vals, refund=True))
        cr.execute(
            "UPDATE account_journal SET sequence_id = %s, refund_sequence_id = %s WHERE id = %s",
            (sequence.id, refund_sequence.id or None, journal.id),
        )
