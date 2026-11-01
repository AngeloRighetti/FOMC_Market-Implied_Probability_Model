# FOMC Market-Implied Probability Model

A quantitative econometric model that extracts market-implied probabilities of Federal Reserve interest rate changes from 30-Day Federal Funds Futures (CME ZQ). 

This project implements a monolithic, zero-dependency Python architecture to calculate the expected post-meeting policy rates, decompose them into discrete 25-basis-point step probabilities, and compute the cumulative terminal rate distribution across a 12-month rolling horizon.

## Architecture & Features

- **Monolithic Design:** The entire extraction kernel and terminal rendering dashboard are contained in a single `main.py` file. No external libraries or virtual environments are required.
- **Pure Mathematical Kernel:** Implements rigorous forward chaining and discrete convolution based on standard monetary policy expectations literature.
- **Boundary Handling:** Includes the Next-Month Rule for robust estimation when FOMC meetings occur late in the calendar month.
- **High-Precision CLI Dashboard:** Renders conditional meeting probabilities and cumulative distributions directly in the terminal using sub-character Unicode resolution.

## Data Sources & Manual Updating

To run the model with real-time accuracy, you must update the manual input section at the top of `main.py` using live market data.

### 1. Spot EFFR (Effective Federal Funds Rate)
The baseline rate from which the forward chain begins.
* **Source:** [Federal Reserve Bank of New York - EFFR](https://www.newyorkfed.org/markets/reference-rates/effr) or [FRED (DFF)](https://fred.stlouisfed.org/series/DFF).
* **Action:** Update the `SPOT_EFFR` and `AS_OF_DATE` variables.

### 2. 30-Day Federal Funds Futures (ZQ)
The settlement prices of the futures contracts determine the implied average rates for upcoming months.
* **Source:** [CME Group - 30-Day Fed Funds Futures Quotes](https://www.cmegroup.com/markets/interest-rates/stirs/30-day-federal-fund.html) or platforms like [RateProbability.com](https://rateprobability.com/).
* **Action:** Update the `FUTURES_PRICES` dictionary. Input the market price (e.g., `95.937`). The model automatically converts this to the implied rate ($R = 100 - P$).

### 3. FOMC Calendar
The schedule of monetary policy decision days.
* **Source:** [Federal Reserve - Meeting Calendars](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).
* **Action:** Maintain the `FOMC_CALENDAR` list. Remove past meetings to keep the 12-month forward horizon clean. Label months without meetings as "Anchor months" by setting `decision_day: None`.

## Usage

**Prerequisites:** Python 3.x (Standard Library only).

1. Clone the repository.
2. Update the input variables in `main.py` using the sources above.
3. Execute the model:

```bash
python3 main.py