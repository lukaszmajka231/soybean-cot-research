import requests
import pandas as pd
import yfinance as yf
from scipy.stats import fisher_exact
pd.set_option('future.no_silent_downcasting', True)


COT_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"

grains = [
    {"label": "Corn", "market_names": ["CORN - CHICAGO BOARD OF TRADE"], "ticker": "ZC=F"},
    {"label": "Soybeans", "market_names": ["SOYBEANS - CHICAGO BOARD OF TRADE"], "ticker": "ZS=F"},
    {"label": "Wheat", "market_names": ["WHEAT - CHICAGO BOARD OF TRADE", "WHEAT-SRW - CHICAGO BOARD OF TRADE"], "ticker": "ZW=F"},
]

def run_hit_test(full_dataset, event_dates, N, k):
    results = []

    for event_date in event_dates:
        event_loc = full_dataset.index.get_loc(event_date)

        if event_loc + N >= len(full_dataset):
            continue

        frozen_mean = full_dataset["rolling_mean_price"].iloc[event_loc]
        price_at_event = full_dataset["Close"].iloc[event_loc]
        price_at_future = full_dataset["Close"].iloc[event_loc + N]
        vol_at_event = full_dataset["rolling_std_price_change"].iloc[event_loc]
        if pd.isna(frozen_mean) or pd.isna(vol_at_event):
            continue
        gap_at_event = abs(price_at_event - frozen_mean)
        gap_at_future = abs(price_at_future - frozen_mean)
        distance_closed = gap_at_event - gap_at_future
        hit = distance_closed > (k * vol_at_event)

        results.append({
            "event_date": event_date,
            "distance_closed": distance_closed,
            "hit_threshold": k * vol_at_event,
            "hit": hit
        })

    return pd.DataFrame(results)

def run_grain(label, market_names, ticker, threshold=2.5, N=12, k=1):
    names_clause = ", ".join(f"'{name}'" for name in market_names)
    where_clause = f"market_and_exchange_names IN({names_clause})"

    params = {
        "$where": where_clause,
        "$limit": 50000,
        "$order": "report_date_as_yyyy_mm_dd ASC"
    }
    response = requests.get(COT_URL, params=params)
    response.raise_for_status()

    data = response.json()
    df = pd.DataFrame(data)

    columns_needed = [
        "report_date_as_yyyy_mm_dd",
        "open_interest_all",
        "prod_merc_positions_long",
        "prod_merc_positions_short",
        "swap_positions_long_all",
        "swap__positions_short_all",
        "m_money_positions_long_all",
        "m_money_positions_short_all",
        "other_rept_positions_long",
        "other_rept_positions_short"
    ]

    df_clean = df[columns_needed].copy()

    df_clean["report_date_as_yyyy_mm_dd"] = pd.to_datetime(df_clean["report_date_as_yyyy_mm_dd"])

    df_clean = df_clean.drop_duplicates(subset="report_date_as_yyyy_mm_dd", keep="first")

    numeric_cols = [
        "open_interest_all", "prod_merc_positions_long", "prod_merc_positions_short",
        "swap_positions_long_all", "swap__positions_short_all",
        "m_money_positions_long_all", "m_money_positions_short_all",
        "other_rept_positions_long", "other_rept_positions_short"
    ]

    df_clean[numeric_cols] = df_clean[numeric_cols].apply(pd.to_numeric)

    df_clean["prod_merc_net"] = df_clean["prod_merc_positions_long"] - df_clean["prod_merc_positions_short"]

    df_clean["commercial_net_pct_oi"] = df_clean["prod_merc_net"] / df_clean["open_interest_all"]

    window = 52

    rolling_mean = df_clean["commercial_net_pct_oi"].rolling(window=window, center=False).mean()
    rolling_std = df_clean["commercial_net_pct_oi"].rolling(window=window, center=False).std()

    df_clean["positioning_zscore"] = (df_clean["commercial_net_pct_oi"] - rolling_mean) / rolling_std

    df_clean["is_extreme"] = df_clean["positioning_zscore"].abs() > threshold
    df_clean["is_new_event"] = df_clean["is_extreme"] & (~df_clean["is_extreme"].shift(1).fillna(False).infer_objects(copy=False))

    df_clean["swap_net"] = df_clean["swap_positions_long_all"] - df_clean["swap__positions_short_all"]
    df_clean["m_money_net"] = df_clean["m_money_positions_long_all"] - df_clean["m_money_positions_short_all"]
    df_clean["other_rept_net"] = df_clean["other_rept_positions_long"] - df_clean["other_rept_positions_short"]

    df_clean["publish_date"] = df_clean["report_date_as_yyyy_mm_dd"] + pd.Timedelta(days=3)

    df_price = yf.download(ticker, start="2006-01-01")

    df_price.columns = df_price.columns.get_level_values(0)
    df_price = df_price.reset_index().rename(columns={"Date": "price_date"})

    df_clean = df_clean.sort_values("publish_date")
    df_price = df_price.sort_values("price_date")

    full_dataset = pd.merge_asof(
        df_clean,
        df_price,
        left_on="publish_date",
        right_on="price_date",
        direction="forward"
    )

    full_dataset = full_dataset.set_index("publish_date")

    price_window = 52
    full_dataset["rolling_mean_price"] = full_dataset["Close"].rolling(window=price_window, center=False).mean()
    full_dataset["rolling_std_price"] = full_dataset["Close"].rolling(window=price_window, center=False).std()

    full_dataset["price_change"] = full_dataset["Close"].diff()
    full_dataset["rolling_std_price_change"] = full_dataset["price_change"].rolling(window=price_window, center=False).std()

    full_dataset["price_zscore"] = (full_dataset["Close"] - full_dataset["rolling_mean_price"]) / full_dataset["rolling_std_price"]

    full_dataset["is_price_extreme"] = full_dataset["price_zscore"].abs() > threshold
    full_dataset["is_new_price_event"] = full_dataset["is_price_extreme"] & (~full_dataset["is_price_extreme"].shift(1).fillna(False).infer_objects(copy=False))

    price_zscore_at_positioning_events = full_dataset.loc[full_dataset["is_new_event"], "price_zscore"]
    print(f"{label}: avg abs price z-score at positioning event weeks = {price_zscore_at_positioning_events.abs().mean():.2f}")

    event_dates = full_dataset[full_dataset["is_new_event"]].index
    price_event_dates = full_dataset[full_dataset["is_new_price_event"]].index

    results_df = run_hit_test(full_dataset, event_dates, N, k)
    price_results_df = run_hit_test(full_dataset, price_event_dates, N, k)

    all_baseline_results = []

    for i in range(len(full_dataset) - N):
        frozen_mean = full_dataset["rolling_mean_price"].iloc[i]
        price_now = full_dataset["Close"].iloc[i]
        price_future = full_dataset["Close"].iloc[i + N]
        vol_now = full_dataset["rolling_std_price_change"].iloc[i]

        if pd.isna(frozen_mean) or pd.isna(vol_now):
            continue

        gap_now = abs(price_now - frozen_mean)
        gap_future = abs(price_future - frozen_mean)
        distance_closed = gap_now - gap_future
        hit = distance_closed > (k * vol_now)

        all_baseline_results.append({"hit": hit})

    baseline_df = pd.DataFrame(all_baseline_results)

    event_hits = results_df["hit"].sum()
    event_misses = len(results_df) - event_hits

    baseline_hits = baseline_df["hit"].sum()
    baseline_misses = len(baseline_df) - baseline_hits

    contingency_table = [
        [event_hits, event_misses],
        [baseline_hits, baseline_misses]
    ]

    odds_ratio, p_value = fisher_exact(contingency_table)

    price_event_hits = price_results_df["hit"].sum()
    price_event_misses = len(price_results_df) - price_event_hits

    price_contingency_table = [
        [price_event_hits, price_event_misses],
        [baseline_hits, baseline_misses]
    ]

    price_odds_ratio, price_p_value = fisher_exact(price_contingency_table)

    results_summary = {
        "commodity": label,
        "threshold": threshold,
        "holding_period_weeks": N,
        "usable_events": len(results_df),
        "event_hit_rate": results_df["hit"].mean(),
        "baseline_hit_rate": baseline_df["hit"].mean(),
        "odds_ratio": odds_ratio,
        "p_value": p_value,
        "price_usable_events": len(price_results_df),
        "price_event_hit_rate": price_results_df["hit"].mean(),
        "price_odds_ratio": price_odds_ratio,
        "price_p_value": price_p_value,
    }

    return results_summary


all_results = []
for grain in grains:
    print(f"Running {grain['label']}...")
    result = run_grain(grain["label"], grain["market_names"], grain["ticker"])
    all_results.append(result)

summary_df = pd.DataFrame(all_results)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
print(summary_df)
summary_df.to_csv("grain_significance_summary.csv", index=False)

thresholds_to_test = [2.0, 2.5, 3.0]
holding_periods_to_test = [8, 12, 16]

sweep_results = []
for grain in grains:
    for threshold in thresholds_to_test:
        for N in holding_periods_to_test:
            print(f"Sweeping {grain['label']}, threshold={threshold}, N={N}...")
            result = run_grain(grain["label"], grain["market_names"], grain["ticker"], threshold=threshold, N=N)
            sweep_results.append(result)

sweep_df = pd.DataFrame(sweep_results)
print(sweep_df)
sweep_df.to_csv("parameter_sweep_summary.csv", index=False)