import requests
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt


COT_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"
MARKET_NAME = "SOYBEANS - CHICAGO BOARD OF TRADE"

params = {
    "$where": f"market_and_exchange_names='{MARKET_NAME}'",
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


numeric_cols = [
    "open_interest_all", "prod_merc_positions_long", "prod_merc_positions_short",
    "swap_positions_long_all", "swap__positions_short_all",
    "m_money_positions_long_all", "m_money_positions_short_all",
    "other_rept_positions_long", "other_rept_positions_short"
]

df_clean[numeric_cols] = df_clean[numeric_cols].apply(pd.to_numeric)

df_clean["prod_merc_net"] = df_clean["prod_merc_positions_long"] - df_clean["prod_merc_positions_short"]
df_clean["swap_net"] = df_clean["swap_positions_long_all"] - df_clean["swap__positions_short_all"]
df_clean["m_money_net"] = df_clean["m_money_positions_long_all"] - df_clean["m_money_positions_short_all"]
df_clean["other_rept_net"] = df_clean["other_rept_positions_long"] - df_clean["other_rept_positions_short"]

df_price = yf.download("ZS=F", start="2006-01-01")

df_clean = df_clean.set_index("report_date_as_yyyy_mm_dd")

df_price.columns = df_price.columns.get_level_values(0)

full_dataset = df_clean.join(df_price, how="inner")

print(full_dataset.shape)
print(full_dataset.head())

full_dataset.to_csv("cot_price_merged.csv")

summary_stats = full_dataset.describe()

summary_stats.to_csv("summary_statistics.csv")

fig, ax1 = plt.subplots(figsize=(14, 6))

ax1.plot(full_dataset.index, full_dataset["Close"], color="black", label="ZS=F Price")
ax1.set_ylabel("Price")
ax1.set_xlabel("Date")

ax2 = ax1.twinx()
ax2.plot(full_dataset.index, full_dataset["prod_merc_net"], color="tab:blue", alpha=0.6, label="Producer/Merchant Net Position")
ax2.set_ylabel("Net Position (contracts)")

plt.title("Soybean Price vs. Producer/Merchant Net Position")
fig.tight_layout()
plt.savefig("price_vs_net_position.png")
ax1.legend(loc="upper left")
ax2.legend(loc="upper right")


plt.show()

