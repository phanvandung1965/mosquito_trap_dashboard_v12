# Semantic Measures (DAX blueprint)

```DAX
Total Mosquito = SUM(fact_observation[mosquito_count])

Total Traps = DISTINCTCOUNT(dim_trap[TrapKey])

Active Traps =
CALCULATE(
    DISTINCTCOUNT(dim_trap[TrapKey]),
    dim_trap[current_status] = "active"
)

Offline Traps =
CALCULATE(
    DISTINCTCOUNT(dim_trap[TrapKey]),
    dim_trap[current_status] = "offline"
)

Maintenance Traps =
CALCULATE(
    DISTINCTCOUNT(dim_trap[TrapKey]),
    dim_trap[current_status] = "maintenance"
)

Avg Mosquito per Active Trap = DIVIDE([Total Mosquito], [Active Traps], 0)

Alert Count = COUNTROWS(fact_alert)

Offline Alert Count =
CALCULATE(
    COUNTROWS(fact_alert),
    fact_alert[alert_type] = "offline"
)

High Severity Alerts =
CALCULATE(
    COUNTROWS(fact_alert),
    fact_alert[severity] IN {"high", "critical"}
)

7D Mosquito Rolling =
CALCULATE(
    [Total Mosquito],
    DATESINPERIOD(dim_date[Date], MAX(dim_date[Date]), -7, DAY)
)
```
