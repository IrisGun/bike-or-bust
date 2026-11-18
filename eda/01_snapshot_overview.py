# %% [markdown]
# # EDA 01 - one snapshot of the Citi Bike feeds (static view)
#
# Questions this answers (see docs/problem-statement.md, section 5):
# 1. What does the system look like
# 2. How clean is the data
# 3. How many stations sit near a stock-out right now. It cannot answer anything about time
# (stock-out duration, time-of-day bias): that needs a time series.

# Publishing rule (ADR-001): print and plot aggregates only, no station names, ids
# or coordinates to comply with data privacy requirements.
# Run as a script:  uv run python eda/01_snapshot_overview.py
# Or cell by cell in VS Code: pick the project's .venv as the interpreter/kernel first.
# The script finds the project root and reads .env itself (R2 credentials stay out of the repo).

# %%
import gzip
import json
import os
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from bike_or_bust.storage import storage_from_env

# Works from any working directory (a notebook kernel often starts somewhere else).
try:
    HERE = Path(__file__).resolve().parent  # running as a script
except NameError:
    HERE = Path.cwd()  # running cell by cell: no __file__
ROOT = next(p for p in [HERE, *HERE.parents] if (p / "pyproject.toml").exists())


def load_env_file(path: Path) -> None:
    """Read KEY=VALUE lines into os.environ without overriding what is already set."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env_file(ROOT / ".env")
os.environ.setdefault("STORAGE_BACKEND", "r2")  # the data lives in R2, not on this machine

CITY = os.environ.get("CITY", "nyc")
FIGURES = ROOT / "docs/eda/figures"
FIGURES.mkdir(parents=True, exist_ok=True)
storage = storage_from_env(os.environ)


def latest_snapshot(feed: str) -> tuple[str, dict]:
    keys = [k for k in storage.list_keys(f"city={CITY}/feed={feed}/") if k.endswith(".json.gz")]
    key = keys[-1]
    return key, json.loads(gzip.decompress(storage.get(key)))


# %% [markdown]
# ### 1. Load the latest snapshot of both feeds

# %%
key_s, status_doc = latest_snapshot("station_status")
key_i, info_doc = latest_snapshot("station_information")
print("status slot     :", key_s.rsplit("_", 1)[-1].removesuffix(".json.gz"))
print("information slot:", key_i.rsplit("_", 1)[-1].removesuffix(".json.gz"))
print("source last_updated (status):", status_doc["last_updated"])

status = pd.DataFrame(status_doc["data"]["stations"])
info = pd.DataFrame(info_doc["data"]["stations"])
print(f"rows: status={len(status)} information={len(info)}")

# %% [markdown]
# ### 2. Do the two feeds describe the same stations?

# %%
s_ids, i_ids = set(status.station_id), set(info.station_id)
print("in status only     :", len(s_ids - i_ids))
print("in information only:", len(i_ids - s_ids))
print(
    "duplicate ids      : status",
    status.station_id.duplicated().sum(),
    "| information",
    info.station_id.duplicated().sum(),
)

df = status.merge(info[["station_id", "capacity", "region_id", "station_type"]], on="station_id")
print("joined rows:", len(df))

# %% [markdown]
# ### 3. Which stations count as active? (rules for the stock-out label)

# %%
snapshot_ts = status_doc["last_updated"]
df["active"] = (df.is_installed == 1) & (df.is_renting == 1)
df["placeholder_ts"] = df.last_reported <= 86400
df["age_min"] = (snapshot_ts - df.last_reported).where(~df.placeholder_ts) / 60

classes = pd.Series(
    {
        "active (installed + renting)": int(df.active.sum()),
        "installed, not renting": int(((df.is_installed == 1) & (df.is_renting == 0)).sum()),
        "not installed": int((df.is_installed == 0).sum()),
        "active but not returning": int((df.active & (df.is_returning == 0)).sum()),
        "placeholder last_reported (<= 1 day after epoch)": int(df.placeholder_ts.sum()),
        "active AND placeholder last_reported": int((df.active & df.placeholder_ts).sum()),
    }
)
print(classes.to_string())

act = df[df.active].copy()
age = act.age_min.dropna()
print("\nminutes since the station last reported (active, valid timestamps):")
print(age.describe(percentiles=[0.5, 0.9, 0.99]).round(1).to_string())
print("stale > 60 min:", int((age > 60).sum()), "| > 1 day:", int((age > 1440).sum()))

# %% [markdown]
# ### 4. Stock levels: how close to a stock-out is the system right now?

# %%
act["fill"] = act.num_bikes_available / act.capacity.where(act.capacity > 0)
n = len(act)
print(f"active stations: {n}")
print("bikes available per station:")
print(
    act.num_bikes_available.describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]).round(1).to_string()
)
for lo, hi, label in [(0, 0, "0 bikes (stock-out)"), (1, 2, "1-2 bikes"), (3, 5, "3-5 bikes")]:
    k = int(act.num_bikes_available.between(lo, hi).sum())
    print(f"  {label:22}: {k:4} ({100 * k / n:.1f}%)")
print(f"stations with <= 10% fill: {100 * (act.fill <= 0.10).mean():.1f}%")
print(f"stations with >= 90% fill (no docks to return): {100 * (act.fill >= 0.90).mean():.1f}%")

# %% [markdown]
# ### 5. Internal consistency: do bikes + docks add up to capacity?

# %%
parts = act[
    ["num_bikes_available", "num_bikes_disabled", "num_docks_available", "num_docks_disabled"]
]
gap = act.capacity - parts.sum(axis=1)
print("capacity - (bikes + disabled bikes + docks + disabled docks):")
print("  exactly equal :", int((gap == 0).sum()))
print(
    "  capacity larger (gap > 0):",
    int((gap > 0).sum()),
    "| smaller (gap < 0):",
    int((gap < 0).sum()),
)
print(gap.describe().round(1).to_string())
print(
    "e-bikes available (included in num_bikes_available?):",
    int(act.num_ebikes_available.sum()),
    "of",
    int(act.num_bikes_available.sum()),
    "bikes",
)

# %% [markdown]
# ### 6. Schema drift: fields present only on some stations

# %%
for name, doc in (("station_status", status_doc), ("station_information", info_doc)):
    sets = Counter(tuple(sorted(s)) for s in doc["data"]["stations"])
    common = set.intersection(*(set(k) for k in sets))
    print(f"{name}: {len(sets)} distinct key sets over {sum(sets.values())} rows")
    for keys, count in sets.most_common():
        print(f"  {count:5} rows, extra fields: {sorted(set(keys) - common) or '-'}")

# %% [markdown]
# ### 7. Where is the risk concentrated? (region level, no station detail)

# %%
by_region = (
    act.groupby("region_id")
    .agg(
        stations=("station_id", "size"),
        median_capacity=("capacity", "median"),
        median_bikes=("num_bikes_available", "median"),
        share_le2=("num_bikes_available", lambda s: (s <= 2).mean()),
    )
    .sort_values("stations", ascending=False)
)
print(f"{len(by_region)} regions; the 8 largest:")
print(by_region.head(8).round(2).to_string())
print("\nstation_type:", act.station_type.value_counts().to_dict())

# %% [markdown]
# ### 8. Figures (aggregates only)

# %%
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
act.num_bikes_available.clip(upper=40).hist(bins=41, ax=axes[0])
axes[0].set(
    title="Bikes available per active station (clipped at 40)", xlabel="bikes", ylabel="stations"
)
act.fill.dropna().clip(0, 1).hist(bins=20, ax=axes[1])
axes[1].set(title="Fill ratio (bikes / capacity)", xlabel="fill ratio")
classes.iloc[:3].plot.barh(ax=axes[2])
axes[2].set(title="Station operating state")
fig.tight_layout()
out = FIGURES / f"{CITY}_snapshot_overview.png"
fig.savefig(out, dpi=110)
print("saved", out)
