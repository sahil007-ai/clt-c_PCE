# Data and provenance policy

## Current demo data

All values in `data/fleet.json`, `data/routes.json`, `data/chargers.json`, and
`data/tariffs.json` are seeded demonstration fixtures. The tariff values are
not a published retail tariff and must not be used for billing, procurement, or
operational charging decisions. Cache copies identify themselves as
`cached-fixture`.

## Tariff source finding

The originally proposed MSEDCL MYT order, Case No. 217 of 2024 dated 28 March
2025, is not a safe source for the fixture values. MERC's subsequent daily
order in IA No. 42 of 2025 says that order was stayed while the review petition
was pending and that the earlier FY 2024–25 tariff would remain applicable.
The MERC site also shows later proceedings for Case No. 75 of 2025. Therefore
no rate is copied from either proceeding into this repository without an
operator reviewing the then-current primary order and recording the category,
effective dates, pages, and applicable FAC.

- [MERC daily order in IA No. 42 of 2025](https://merc.gov.in/wp-content/uploads/2025/04/Daily-Order-IA-No.-42-of-2025.pdf)
- [MERC proceedings for the MSEDCL review](https://new.merc.gov.in/hearing/)

## Refresh contract

`live.tariffs.refresh_tariff` and `live.routes.refresh_routes` accept an
explicit caller-supplied fetcher. Each candidate payload must carry `source`,
`fetched_at`, and `validation_status`; tariff data must provide exactly 48
plausible slot prices, and route entries must have positive distance and
duration. Invalid data or a refresh failure leaves the last valid cache in use.

The supplied `python -m live.refresh` command is deliberately cache-only until
an approved source adapter and any required credentials have been configured.
No component fetches the network while building or verifying a schedule.
