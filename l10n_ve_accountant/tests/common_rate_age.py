"""Fixture for the outdated rate warning: VEF company with USD as foreign currency,
user in Caracas, "today" 2026-03-13 and USD rates only up to RATE_DAY (2026-03-10)."""

from datetime import date

from odoo.tests import freeze_time

CARACAS_TZ = "America/Caracas"
RATE_DAY = date(2026, 3, 10)
# 2026-03-13 11:00 in Caracas
FROZEN_NOW = "2026-03-13 15:00:00"


class RateAgeMixin:
    def _setup_rate_age(self):
        self.enterContext(freeze_time(FROZEN_NOW))
        self.company = self.env.ref("base.main_company")
        self.currency_vef = self.env.ref("base.VEF")
        self.currency_usd = self.env.ref("base.USD")
        (self.currency_vef | self.currency_usd).active = True
        self.company.write(
            {
                "currency_id": self.currency_vef.id,
                "foreign_currency_id": self.currency_usd.id,
                "rate_max_age_days": 2,
            }
        )
        self.env.user.write(
            {"tz": CARACAS_TZ, "company_ids": [(4, self.company.id)], "company_id": self.company.id}
        )
        self.env = self.env(context=dict(self.env.context, tz=CARACAS_TZ))
        Rate = self.env["res.currency.rate"].sudo()
        Rate.search(
            [("currency_id", "=", self.currency_usd.id), ("company_id", "=", self.company.id)]
        ).unlink()
        for day, inverse_rate in ((date(2026, 3, 9), 39.0), (RATE_DAY, 40.0)):
            Rate.create(
                {
                    "name": day,
                    "currency_id": self.currency_usd.id,
                    "company_id": self.company.id,
                    "inverse_company_rate": inverse_rate,
                }
            )
