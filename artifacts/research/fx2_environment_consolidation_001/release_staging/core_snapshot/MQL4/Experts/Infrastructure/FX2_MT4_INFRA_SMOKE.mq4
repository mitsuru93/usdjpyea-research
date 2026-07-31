#property strict
#property version   "1.00"
#property description "FX2 neutral infrastructure smoke. No signals and no orders."

input string WorkId = "FX2-RESEARCH-EXECUTION-ENVIRONMENT-CONSOLIDATION-001";
input string RunId = "UNSET";

int g_tick_count = 0;

void Emit(const string event_name)
{
   Print("FX2_INFRA_SMOKE|work_id=", WorkId,
         "|run_id=", RunId,
         "|event=", event_name,
         "|symbol=", Symbol(),
         "|period=", IntegerToString(Period()),
         "|build=", IntegerToString((int)TerminalInfoInteger(TERMINAL_BUILD)),
         "|ticks=", IntegerToString(g_tick_count),
         "|orders_total=", IntegerToString(OrdersTotal()));
}

int OnInit()
{
   Emit("OnInit");
   if(OrdersTotal() != 0)
      Print("FX2_INFRA_SMOKE|event=GuardFailure|reason=unexpected_existing_orders");
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   g_tick_count++;
   if(g_tick_count == 1)
      Emit("OnTick");
}

void OnDeinit(const int reason)
{
   Emit("OnDeinit");
   Print("FX2_INFRA_SMOKE|event=Final|reason=", IntegerToString(reason),
         "|runtime_error=", IntegerToString(GetLastError()),
         "|orders_sent=0");
}
