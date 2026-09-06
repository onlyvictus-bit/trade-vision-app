# V1 pre-test results (H1/H2/H3)

symbols=['RELIANCE', 'BEL', 'TCS', 'INFY', 'HDFCBANK'] start=2025-01-01 labeled_trades=11043

## H1_narrow_vs_wide: breakout NARROW-day R vs WIDE-day R
n1=5661 n2=115 p=0.4554 (Holm<=0.0167) r=+0.041 med1=-0.075 med2=-0.141 -> **NO_GO**

## H2_aligned_vs_counter: gap-aligned R vs counter-gap R
n1=6510 n2=4533 p=0.5224 (Holm<=0.0500) r=+0.007 med1=-1.032 med2=-0.706 -> **NO_GO**

## H3_cpr_split: CPR-class separation (same as H1 by construction)
n1=5661 n2=115 p=0.4554 (Holm<=0.0250) r=+0.041 med1=-0.075 med2=-0.141 -> **NO_SEPARATION**

## H3_tercile_split: close-tercile high vs low separation
n1=1800 n2=2054 p=0.3290 (Holm<=0.0125) r=+0.018 med1=-0.106 med2=-0.104 -> **NO_SEPARATION**

