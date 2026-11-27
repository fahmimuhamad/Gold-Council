# MT5 export: the one thing that needs your Mac

`GoldCouncilHistoryExport.mq5` is a **read-only script**. It places no trades and does not export your login, account number or balance. Only the account currency is recorded.
Status: **written but NOT compiled or run.** It was written in a Linux container, which has no MetaEditor. It may have compile errors that I can fix once you send them.

## Steps (about 5 minutes)
1. Open MT5 → **File → Open Data Folder** → go to `MQL5/Scripts/` → copy `GoldCouncilHistoryExport.mq5` into it.
2. Press **F4** (MetaEditor) → open the file → **Compile**. If errors appear, copy the text from the *Errors* tab and send it to me.
3. Back in MT5 → Navigator → Scripts → drag **GoldCouncilHistoryExport** onto any chart.
4. In the inputs, set `InpSymbols` to your broker's exact gold/silver names (for example `XAUUSD.vx,XAGUSD.vx`), then press OK.
5. Check the **Experts** tab for the "GC: export … finished" line, which prints the folder path.
6. Upload that folder's CSV files and `manifest.json` here. The manifest tells me the broker's time offset.

## Before the first import
Broker server time is **not** UTC. Many brokers use GMT+2 in winter and GMT+3 in summer, switching on **US** daylight-saving dates. The manifest records the offset at export time only. I check the switching dates against the data around the weekly open before importing. The importer supports this clock as `--tz America/New_York+7`.
