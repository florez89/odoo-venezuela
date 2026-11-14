def ensure_rate_in_force(env, company, inverse_rate=36.0, date="2000-01-01"):
    """Give `company`'s foreign currency a rate in force from `date` on.

    `res.currency.rate.compute_rate()` raises when the currency has no rate dated
    on or before the document date, and a fresh database has no rates at all, so
    a test creating documents needs its own. An old date covers every later
    document date (the rate in force is the latest one on or before that date).
    Left untouched when that currency already has a rate on `date`.
    """
    currency = company.foreign_currency_id
    root = company.root_id or company
    if not currency or currency == company.currency_id:
        return
    Rate = env["res.currency.rate"]
    domain = [("currency_id", "=", currency.id), ("company_id", "=", root.id), ("name", "=", date)]
    if not Rate.search_count(domain):
        Rate.create(
            {
                "currency_id": currency.id,
                "company_id": root.id,
                "name": date,
                "inverse_company_rate": inverse_rate,
            }
        )
