# Methodology & Formulas

This document describes the financial formulas, statistical methods, and assumptions used in the analytics engine.

---

## 1. Return Calculations

### Daily Return
$$
r_t = \frac{P_t^{adj} - P_{t-1}^{adj}}{P_{t-1}^{adj}}
$$
Where $P_t^{adj}$ is the adjusted closing price on day $t$. Adjusted prices account for stock splits and dividends.

### Cumulative Return
$$
R_{cum} = \prod_{i=1}^{T}(1 + r_i) - 1
$$
Geometric compounding of daily returns from the start date to date $T$.

### Annualized Return
$$
R_{ann} = (1 + R_{cum})^{\frac{252}{T}} - 1
$$
Where 252 is the standard number of trading days per year.

### Weighted Portfolio Return
$$
R_{portfolio,t} = \sum_{i=1}^{N} w_i \cdot r_{i,t}
$$
Where $w_i$ is the weight of stock $i$ based on current market value allocation.

---

## 2. Risk Metrics

### Annualized Volatility
$$
\sigma_{ann} = \sigma_{daily} \times \sqrt{252}
$$
Standard deviation of daily returns, scaled to annual terms.

### Sharpe Ratio
$$
S = \frac{R_{ann} - R_f}{\sigma_{ann}}
$$
Where $R_f$ is the risk-free rate (US 10-Year Treasury yield). Measures excess return per unit of total risk.

**Interpretation**: Sharpe > 1.0 is good, > 2.0 is very good, > 3.0 is excellent.

### Sortino Ratio
$$
Sortino = \frac{R_{ann} - R_f}{\sigma_{downside}}
$$
Where $\sigma_{downside}$ is the standard deviation of only negative returns. Penalizes only downside volatility.

### Value at Risk (VaR) — Historical Method
$$
VaR_{95\%} = \text{5th percentile of return distribution}
$$
The maximum expected daily loss at 95% confidence. E.g., VaR of -2.1% means "on 95% of days, the portfolio won't lose more than 2.1%."

### Conditional VaR (CVaR / Expected Shortfall)
$$
CVaR_{95\%} = E[r \mid r \leq VaR_{95\%}]
$$
The average loss on days when the loss exceeds VaR. A more conservative risk measure.

### Max Drawdown
$$
MDD = \min_t \left(\frac{P_t - P_{peak,t}}{P_{peak,t}}\right)
$$
Where $P_{peak,t} = \max_{\tau \leq t} P_\tau$. The largest peak-to-trough decline during the observation period.

---

## 3. Market Risk Metrics (CAPM)

### Beta
$$
\beta = \frac{Cov(r_i, r_m)}{Var(r_m)}
$$
Measures the stock's sensitivity to market movements. $\beta > 1$ means more volatile than the market, $\beta < 1$ means less volatile.

### Alpha (Jensen's Alpha)
$$
\alpha = R_p - [R_f + \beta \cdot (R_m - R_f)]
$$
Excess return above what CAPM predicts. Positive alpha indicates outperformance.

### Tracking Error
$$
TE = \sigma(r_p - r_b)
$$
Standard deviation of the difference between portfolio and benchmark returns.

### Information Ratio
$$
IR = \frac{R_p - R_b}{TE}
$$
Excess return over benchmark per unit of tracking error.

---

## 4. Diversification Metrics

### Herfindahl-Hirschman Index (HHI)
$$
HHI = \sum_{i=1}^{N} w_i^2
$$
Measures portfolio concentration. Lower HHI = more diversified. Range: $1/N$ (perfectly diversified) to 1.0 (single stock).

### Correlation
$$
\rho_{i,j} = \frac{Cov(r_i, r_j)}{\sigma_i \cdot \sigma_j}
$$
Pearson correlation between daily returns of two stocks. Range: -1 (perfect inverse) to +1 (perfect positive).

---

## 5. Rolling Calculations

All rolling metrics use the following lookback windows:
- **30-day** — Short-term (approximately 1.5 months)
- **60-day** — Medium-term (approximately 3 months)
- **90-day** — Longer-term (approximately 4.5 months)

Rolling calculations use a trailing window of the specified number of **trading days**.

---

## 6. Assumptions & Conventions

| Assumption | Value | Rationale |
|---|---|---|
| Trading days per year | 252 | US market standard |
| Risk-free rate source | US 10-Year Treasury (^TNX) | Industry standard proxy |
| Benchmark | S&P 500 (^GSPC) | Most common US equity benchmark |
| Return type | Simple returns | Used for individual assets |
| Portfolio returns | Weighted simple returns | Standard for portfolio aggregation |
| Price basis | Adjusted close | Accounts for splits and dividends |
| VaR method | Historical simulation | Non-parametric, no distribution assumptions |
| Rebalancing | None (buy-and-hold) | Weights change with market movements |

---

## References

- Sharpe, W.F. (1966). "Mutual Fund Performance." *Journal of Business*.
- Sortino, F.A. & van der Meer, R. (1991). "Downside Risk." *Journal of Portfolio Management*.
- Jorion, P. (2006). *Value at Risk: The New Benchmark for Managing Financial Risk*.
- Bodie, Kane, Marcus. *Investments* (12th Edition). McGraw Hill.
