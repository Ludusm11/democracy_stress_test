# ESM and EFSF loan flows

`OverviewData.csv`: one row per payment, with columns `Company` (ESM or EFSF), `Country`, `Payment Date` (day/month/year), `Type` and `Payment` in euro. Added by the team on 15 November 2026; the source page was not recorded (it matches the loan data the ESM and EFSF publish). Negative amounts are money paid out to the country (disbursements), positive `Repayment` rows are repayments already made, and `ScheduledRepayment` rows are future repayments.

Coverage: EFSF loans to Greece, Ireland and Portugal; ESM loans to Cyprus, Greece and Spain (bank recapitalisation). **Not included:** the EFSM loans to Ireland and Portugal, Greece's bilateral Greek Loan Facility (2010), IMF loans and EU balance-of-payments loans (Latvia, Hungary, Romania), so programme sizes built from this file are lower bounds.
