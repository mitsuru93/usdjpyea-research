#!/usr/bin/env python3
"""Event lifecycle simulator for the frozen native H4/H1 family."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
from usdjpy_native_htf_state_data_v1 import PIP,execution_index,hard_excluded

@dataclass
class Pending:
 side:int;h4_info:pd.Timestamp;remaining_future_h1:int=4
@dataclass
class Position:
 side:int;entry_index:int;entry_info:pd.Timestamp;entry_reason:str

def simulate_fold(candidate_id:str,h4:pd.DataFrame,h1:pd.DataFrame,m15:pd.DataFrame,start:pd.Timestamp,end:pd.Timestamp)->tuple[pd.DataFrame,pd.DataFrame]:
 h4e=h4[(h4.information_utc>=start)&(h4.information_utc<end)][["information_utc","h4_state","h4_transition"]].copy();h4e["kind"]="H4"
 h1e=h1[(h1.information_utc>=start)&(h1.information_utc<end)][["information_utc","h1_state"]].copy();h1e["kind"]="H1"
 events=pd.concat([h4e,h1e],ignore_index=True,sort=False);events["order"]=events.kind.map({"H4":0,"H1":1});events=events.sort_values(["information_utc","order"]).reset_index(drop=True)
 fm=m15[(m15.logical_utc>=start)&(m15.logical_utc<end)].copy().reset_index(drop=True);times=fm.logical_utc.to_numpy(dtype="datetime64[ns]")
 pending:Pending|None=None;position:Position|None=None;last_h1=0;signals:list[dict[str,Any]]=[];trades:list[dict[str,Any]]=[]
 def close(info:pd.Timestamp,reason:str,boundary:bool=False)->None:
  nonlocal position
  assert position is not None
  idx=len(fm)-1 if boundary else execution_index(times,info)
  if idx is None:return
  entry=fm.iloc[position.entry_index];exit_row=fm.iloc[idx];gross=position.side*(float(exit_row.open)-float(entry.open))/PIP;cost=float(entry.default_cost_pips);severe=3*cost+1
  trades.append({"candidate_id":candidate_id,"entry_logical_utc":entry.logical_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),"entry_accepted_ts":entry.accepted_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),"exit_logical_utc":exit_row.logical_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),"exit_accepted_ts":exit_row.accepted_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),"entry_information_utc":position.entry_info.strftime("%Y-%m-%dT%H:%M:%SZ"),"exit_information_utc":info.strftime("%Y-%m-%dT%H:%M:%SZ"),"side":position.side,"entry_price":float(entry.open),"exit_price":float(exit_row.open),"gross_pips":gross,"default_cost_pips":cost,"severe_cost_pips":severe,"default_net_pips":gross-cost,"severe_net_pips":gross-severe,"exit_reason":reason,"boundary_liquidation":boundary,"entry_date":entry.logical_utc.strftime("%Y-%m-%d"),"entry_month":entry.logical_utc.strftime("%Y-%m"),"entry_quarter":f"{entry.logical_utc.year}-Q{(entry.logical_utc.month-1)//3+1}","duration_hours":float((exit_row.logical_utc-entry.logical_utc).total_seconds()/3600),"entry_reason":position.entry_reason});position=None
 for info,group in events.groupby("information_utc",sort=True):
  info=pd.Timestamp(info);hr=group[group.kind=="H4"];h1r=group[group.kind=="H1"];transition=int(hr.h4_transition.iloc[0]) if len(hr) else 0;h4state=int(hr.h4_state.iloc[0]) if len(hr) else 0
  if len(h1r):last_h1=int(h1r.h1_state.iloc[0])
  reason=None
  if position is not None:
   if transition==-position.side:reason="H4_OPPOSITE_TRANSITION"
   elif len(h1r) and last_h1==-position.side:reason="H1_OPPOSITE_STATE"
  if reason:close(info,reason)
  if transition in (-1,1):
   pending=Pending(transition,info,4);signals.append({"candidate_id":candidate_id,"event":"H4_TRANSITION","information_utc":info.strftime("%Y-%m-%dT%H:%M:%SZ"),"side":transition,"detail":f"h4_state={h4state}"})
  if pending is not None and len(h1r):
   if last_h1==pending.side and position is None:
    idx=execution_index(times,info)
    if idx is not None:
     row=fm.iloc[idx]
     if not hard_excluded(pd.Timestamp(row.logical_utc)):
      position=Position(pending.side,idx,info,"H4_TRANSITION_H1_CONFIRM");signals.append({"candidate_id":candidate_id,"event":"ENTRY","information_utc":info.strftime("%Y-%m-%dT%H:%M:%SZ"),"side":pending.side,"detail":row.logical_utc.strftime("%Y-%m-%dT%H:%M:%SZ")})
     else:signals.append({"candidate_id":candidate_id,"event":"CANCEL_HARD_EXCLUSION","information_utc":info.strftime("%Y-%m-%dT%H:%M:%SZ"),"side":pending.side,"detail":row.logical_utc.strftime("%Y-%m-%dT%H:%M:%SZ")})
    pending=None
   elif info>pending.h4_info:
    pending.remaining_future_h1-=1
    if pending.remaining_future_h1<=0:
     signals.append({"candidate_id":candidate_id,"event":"CANCEL_CONFIRMATION_TIMEOUT","information_utc":info.strftime("%Y-%m-%dT%H:%M:%SZ"),"side":pending.side,"detail":"four_future_H1_bars"});pending=None
 if position is not None and len(fm):close(end,"BOUNDARY_LIQUIDATION",True)
 return pd.DataFrame(signals),pd.DataFrame(trades)
