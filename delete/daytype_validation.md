# Day-type validation (prediction vs completed-session outcome)

sessions=2685 coverage={'TREND_DAY': 2257, 'RANGE_DAY': 428}

## Confusion (predicted -> actual)
- RANGE_DAY->MIXED: 196
- RANGE_DAY->RANGE_DAY: 106
- RANGE_DAY->TREND_DAY: 126
- TREND_DAY->MIXED: 957
- TREND_DAY->RANGE_DAY: 622
- TREND_DAY->TREND_DAY: 678

TREND precision (predicted TREND that trended): 0.3
RANGE precision (predicted RANGE that ranged): 0.248
Directional hit rate: 0.152
