//+------------------------------------------------------------------+
//| GoldCouncilHistoryExport.mq5                                     |
//| READ-ONLY script: exports completed OHLC bars + symbol specs.    |
//| It places NO orders and reads NO account credentials.            |
//| STATUS: written in a Linux container, NOT compiled or run yet.   |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input string InpSymbols    = "XAUUSD,XAGUSD";      // exact broker symbols, comma separated (e.g. XAUUSD.vx)
input string InpTimeframes = "D1,H4,H1,M15,M5";     // timeframes to export
input int    InpBars       = 100000;                // max completed bars per symbol/timeframe
input string InpFolder     = "GoldCouncil";         // folder inside the terminal's COMMON Files folder

#define SCHEMA_VERSION "gc-export-1.0"

ENUM_TIMEFRAMES TfFromString(const string s)
  {
   if(s=="M1")  return PERIOD_M1;
   if(s=="M5")  return PERIOD_M5;
   if(s=="M15") return PERIOD_M15;
   if(s=="M30") return PERIOD_M30;
   if(s=="H1")  return PERIOD_H1;
   if(s=="H4")  return PERIOD_H4;
   if(s=="D1")  return PERIOD_D1;
   if(s=="W1")  return PERIOD_W1;
   return (ENUM_TIMEFRAMES)-1;
  }

string Iso(const datetime t)
  {
   MqlDateTime d; TimeToStruct(t,d);
   return StringFormat("%04d-%02d-%02d %02d:%02d:%02d",d.year,d.mon,d.day,d.hour,d.min,d.sec);
  }

string Json(const string s) { string r=s; StringReplace(r,"\\","\\\\"); StringReplace(r,"\"","\\\""); return "\""+r+"\""; }

//--- export one symbol/timeframe; returns rows written or -1
int ExportBars(const string sym,const string tfName,const string runId)
  {
   ENUM_TIMEFRAMES tf=TfFromString(tfName);
   if((int)tf<0) { PrintFormat("GC: unknown timeframe %s",tfName); return -1; }
   MqlRates rates[];
   ArraySetAsSeries(rates,false);
   // start position 1 = skip the currently forming bar (completed bars only)
   int n=CopyRates(sym,tf,1,InpBars,rates);
   if(n<=0) { PrintFormat("GC: CopyRates failed %s %s err=%d",sym,tfName,GetLastError()); return -1; }

   string staging=InpFolder+"\\staging\\"+runId+"_"+sym+"_"+tfName+".csv";
   string final  =InpFolder+"\\"+runId+"\\"+sym+"_"+tfName+".csv";
   int h=FileOpen(staging,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE) { PrintFormat("GC: cannot open %s err=%d",staging,GetLastError()); return -1; }
   FileWrite(h,"time","open","high","low","close","tick_volume","spread","real_volume");
   int digits=(int)SymbolInfoInteger(sym,SYMBOL_DIGITS);
   for(int i=0;i<n;i++)
      FileWrite(h,Iso(rates[i].time),
                DoubleToString(rates[i].open,digits),DoubleToString(rates[i].high,digits),
                DoubleToString(rates[i].low,digits),DoubleToString(rates[i].close,digits),
                (string)rates[i].tick_volume,(string)rates[i].spread,(string)rates[i].real_volume);
   FileClose(h);
   if(!FileMove(staging,FILE_COMMON,final,FILE_COMMON|FILE_REWRITE))
     { PrintFormat("GC: move failed %s err=%d",final,GetLastError()); return -1; }
   return n;
  }

string SpecJson(const string sym)
  {
   return StringFormat("{\"symbol\":%s,\"digits\":%d,\"point\":%.10g,\"tick_size\":%.10g,\"tick_value\":%.10g,"
      "\"contract_size\":%.10g,\"volume_min\":%.10g,\"volume_max\":%.10g,\"volume_step\":%.10g,"
      "\"stops_level_points\":%d,\"freeze_level_points\":%d,\"currency_profit\":%s,\"currency_margin\":%s}",
      Json(sym),(int)SymbolInfoInteger(sym,SYMBOL_DIGITS),SymbolInfoDouble(sym,SYMBOL_POINT),
      SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(sym,SYMBOL_TRADE_TICK_VALUE),
      SymbolInfoDouble(sym,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(sym,SYMBOL_VOLUME_MIN),
      SymbolInfoDouble(sym,SYMBOL_VOLUME_MAX),SymbolInfoDouble(sym,SYMBOL_VOLUME_STEP),
      (int)SymbolInfoInteger(sym,SYMBOL_TRADE_STOPS_LEVEL),(int)SymbolInfoInteger(sym,SYMBOL_TRADE_FREEZE_LEVEL),
      Json(SymbolInfoString(sym,SYMBOL_CURRENCY_PROFIT)),Json(SymbolInfoString(sym,SYMBOL_CURRENCY_MARGIN)));
  }

void OnStart()
  {
   datetime server=TimeTradeServer(), gmt=TimeGMT();
   string runId=StringFormat("export_%I64d",(long)gmt);
   string syms[], tfs[];
   int ns=StringSplit(InpSymbols,',',syms), nt=StringSplit(InpTimeframes,',',tfs);
   string files="", specs="";
   int failures=0;
   for(int s=0;s<ns;s++)
     {
      string sym=syms[s]; StringTrimLeft(sym); StringTrimRight(sym);
      if(!SymbolSelect(sym,true)) { PrintFormat("GC: symbol not available: %s",sym); failures++; continue; }
      specs+=(specs==""?"":",")+SpecJson(sym);
      for(int t=0;t<nt;t++)
        {
         string tf=tfs[t]; StringTrimLeft(tf); StringTrimRight(tf);
         int rows=ExportBars(sym,tf,runId);
         if(rows<0) { failures++; continue; }
         files+=(files==""?"":",")+StringFormat("{\"symbol\":%s,\"timeframe\":%s,\"rows\":%d}",Json(sym),Json(tf),rows);
        }
     }
   // Manifest: no account number, login, server name or balance is written.
   string manifest=StringFormat("{\"schema_version\":%s,\"run_id\":%s,\"exported_at_gmt\":%s,"
      "\"server_time_at_export\":%s,\"server_minus_gmt_seconds\":%I64d,"
      "\"note\":\"bar times are BROKER SERVER time; offset is valid only at export time (DST changes it)\","
      "\"account_currency\":%s,\"failures\":%d,\"files\":[%s],\"symbols\":[%s]}",
      Json(SCHEMA_VERSION),Json(runId),Json(Iso(gmt)),Json(Iso(server)),(long)(server-gmt),
      Json(AccountInfoString(ACCOUNT_CURRENCY)),failures,files,specs);
   int h=FileOpen(InpFolder+"\\"+runId+"\\manifest.json",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(h!=INVALID_HANDLE) { FileWriteString(h,manifest); FileClose(h); }
   // Ready marker is written LAST: Python must ignore folders without it (partial exports).
   h=FileOpen(InpFolder+"\\"+runId+"\\READY",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(h!=INVALID_HANDLE) { FileWriteString(h,runId); FileClose(h); }
   PrintFormat("GC: export %s finished, failures=%d. Folder: %s\\%s",runId,failures,
               TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\"+InpFolder,runId);
  }
