# MT5 export: the one thing that needs your Mac

`GoldCouncilHistoryExport.mq5` is a **read-only script**. It places no trades and does not export your login, account number or balance. Only the account currency is recorded.
Status: **written but NOT compiled or run.** It was written in a Linux container, which has no MetaEditor. It may have compile errors that I can fix once you send them.

## Steps (about 5 minutes)
1. Open MT5 → **File → Open Data Folder** → `MQL5/Scripts/` → copy in the NEW `GoldCouncilHistoryExport.mq5` (replace the old one).
2. Press **F4** (MetaEditor) → open it → **Compile**.
3. In MT5 → Navigator → Scripts → drag **GoldCouncilHistoryExport** onto any chart.
4. Inputs: set `InpSymbols` to your exact gold name (e.g. `XAUUSD.vx`). Leave `InpTimeframes = H1` and `InpBars = 50000`. Press OK.
5. The **Experts** tab prints the folder. Open it in Finder, select `XAUUSD_H1.csv` and `manifest.json` → right-click → **Compress**. That gives one small .zip (about 1 MB).
6. Upload the .zip here.
7. Later (optional): run again with `InpTimeframes = M15` and upload that zip separately. One timeframe per upload keeps each file small.

## Before the first import
Broker server time is **not** UTC. Many brokers use GMT+2 in winter and GMT+3 in summer, switching on **US** daylight-saving dates. The manifest records the offset at export time only. I check the switching dates against the data around the weekly open before importing. The importer supports this clock as `--tz America/New_York+7`.
