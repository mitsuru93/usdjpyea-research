#!/usr/bin/env python3
from __future__ import annotations
import argparse, calendar, csv, datetime as dt, gzip, hashlib, io, json, math, os, tarfile
from collections import Counter, defaultdict
from pathlib import Path

WORK_ID='USDJPY-DATA-2020-2022-TICK-AUTHORITY-001'
SOURCE='dukascopy_bi5'
SYMBOL='USDJPY'
PIP_SIZE=0.01
TIMEFRAMES={'M1':60,'M5':300,'M15':900,'H1':3600,'H4':14400,'D1':86400}
NORMALIZED_FIELDS=['timestamp_utc','bid','ask','spread_price','spread_pips','symbol','source','source_file','year','month','trading_date_utc','sequence']

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def write_json(path:Path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')

def parse_ts(s:str)->dt.datetime:
    return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(dt.timezone.utc)

def fmt_ts(x:dt.datetime)->str:
    return x.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

def bucket_start(ts:dt.datetime,secs:int)->dt.datetime:
    epoch=int(ts.timestamp()); return dt.datetime.fromtimestamp(epoch-epoch%secs,tz=dt.timezone.utc)

def easter_date(year:int)->dt.date:
    a=year%19;b=year//100;c=year%100;d=b//4;e=b%4;f=(b+8)//25;g=(b-f+1)//3
    h=(19*a+b-d-g+15)%30;i=c//4;k=c%4;l=(32+2*e+2*i-h-k)%7;m=(a+11*h+22*l)//451
    month=(h+l-7*m+114)//31;day=((h+l-7*m+114)%31)+1
    return dt.date(year,month,day)

def known_holidays(year:int)->set[dt.date]:
    easter=easter_date(year)
    return {dt.date(year,1,1),dt.date(year,12,24),dt.date(year,12,25),dt.date(year,12,26),dt.date(year,12,31),easter-dt.timedelta(days=2),easter+dt.timedelta(days=1)}

def classify_gap(a:dt.datetime,b:dt.datetime)->str:
    dates={a.date()+dt.timedelta(days=i) for i in range((b.date()-a.date()).days+1)}
    if a.weekday()>=4 and any(d.weekday()>=5 for d in dates): return 'WEEKEND_MARKET_CLOSE'
    if any(d in known_holidays(d.year) for d in dates): return 'KNOWN_HOLIDAY_MARKET_CLOSE'
    if (b-a).total_seconds()<=3*3600 and (a.hour>=20 or b.hour<=2): return 'ROLLOVER_OR_THIN_MARKET'
    return 'UNEXPLAINED_INTRAWEEK_GAP'

class BarSink:
    def __init__(self,root:Path):
        self.root=root; self.files={}; self.writers={}; self.current={}; self.counts=Counter(); self.tick_sums=Counter()
        for tf in TIMEFRAMES:
            for side in ('bid','ask'):
                p=root/tf/f'{side}.csv';p.parent.mkdir(parents=True,exist_ok=True)
                f=p.open('w',newline='',encoding='utf-8');w=csv.writer(f,lineterminator='\n')
                w.writerow(['timestamp_utc','side','timeframe','open','high','low','close','first_tick_timestamp_utc','last_tick_timestamp_utc','tick_count'])
                self.files[(tf,side)]=f;self.writers[(tf,side)]=w
    def add(self,ts:dt.datetime,bid:float,ask:float):
        for tf,secs in TIMEFRAMES.items():
            start=bucket_start(ts,secs)
            for side,price in (('bid',bid),('ask',ask)):
                k=(tf,side);cur=self.current.get(k)
                if cur is None or cur['start']!=start:
                    if cur is not None:self._flush(k,cur)
                    cur={'start':start,'open':price,'high':price,'low':price,'close':price,'first':ts,'last':ts,'ticks':1};self.current[k]=cur
                else:
                    cur['high']=max(cur['high'],price);cur['low']=min(cur['low'],price);cur['close']=price;cur['last']=ts;cur['ticks']+=1
    def _flush(self,k,cur):
        tf,side=k;self.writers[k].writerow([fmt_ts(cur['start']),side,tf,f"{cur['open']:.8f}",f"{cur['high']:.8f}",f"{cur['low']:.8f}",f"{cur['close']:.8f}",fmt_ts(cur['first']),fmt_ts(cur['last']),cur['ticks']]);self.counts[k]+=1;self.tick_sums[k]+=cur['ticks']
    def close(self):
        for k,cur in list(self.current.items()):self._flush(k,cur)
        for f in self.files.values():f.close()
        out={}
        for (tf,side),f in self.files.items():
            src=Path(f.name);dst=src.with_suffix('.csv.gz')
            with src.open('rb') as i,dst.open('wb') as raw:
                with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=9) as gz:
                    for b in iter(lambda:i.read(1024*1024),b''):gz.write(b)
            src.unlink();out[f'{tf}_{side}']={'path':dst.as_posix(),'rows':self.counts[(tf,side)],'tick_count_sum':self.tick_sums[(tf,side)],'bytes':dst.stat().st_size,'sha256':sha256_file(dst)}
        return out

def deterministic_tar_gz(out:Path, base:Path, paths:list[Path]):
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=9) as gz:
            with tarfile.open(fileobj=gz,mode='w') as tar:
                for p in sorted(paths,key=lambda x:x.as_posix()):
                    arc=p.relative_to(base).as_posix();info=tar.gettarinfo(str(p),arcname=arc);info.mtime=0;info.uid=0;info.gid=0;info.uname='';info.gname=''
                    if p.is_file():
                        with p.open('rb') as fh:tar.addfile(info,fh)
                    else:tar.addfile(info)

def percentile(sample:list[float],q:float):
    if not sample:return None
    xs=sorted(sample);idx=min(len(xs)-1,max(0,int(round(q*(len(xs)-1)))));return xs[idx]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--year',type=int,required=True);ap.add_argument('--month',type=int,required=True);ap.add_argument('--download-root',required=True);ap.add_argument('--download-manifest',required=True);ap.add_argument('--download-summary',required=True);ap.add_argument('--out',required=True);ap.add_argument('--source-sha',required=True);args=ap.parse_args()
    y,m=args.year,args.month;role='WARMUP_ONLY' if y==2019 else 'ANALYSIS_PERIOD'
    root=Path(args.download_root);out=Path(args.out);out.mkdir(parents=True,exist_ok=True);qc=out/'qc';bars_root=out/'bars';assets=out/'release_assets';qc.mkdir(exist_ok=True);assets.mkdir(exist_ok=True)
    attempts=[]
    for line in Path(args.download_manifest).read_text(encoding='utf-8').splitlines():
        if line.strip():attempts.append(json.loads(line))
    final={r['hour_start_utc']:r for r in attempts}
    downloaded=[r for r in final.values() if r['status']=='downloaded']
    decoded_files=[];source_files=[];missing_source=[]
    for r in sorted(downloaded,key=lambda x:x['hour_start_utc']):
        dp=root/r['decoded_csv_path'];sp=root/r['source_bi5_path']
        if not dp.exists() or not sp.exists():missing_source.append(r['hour_start_utc'])
        else:decoded_files.append((r,dp));source_files.append(sp)
    normalized=assets/f'USDJPY_DUKASCOPY_NORMALIZED_TICKS_{y}_{m:02d}.csv.gz'
    raw_csv=out/'normalized.csv'
    f=raw_csv.open('w',newline='',encoding='utf-8');w=csv.DictWriter(f,fieldnames=NORMALIZED_FIELDS,lineterminator='\n');w.writeheader()
    bars=BarSink(bars_root)
    total=0;first_ts=last_ts=prev_ts=None;prev_row=None;dup_ts=dup_row=out_of_order=0;missing_bid=missing_ask=ask_lt_bid=zero_spread=negative_spread=zero_price=0;weekend_ticks=0
    spread_sum=0.0;spread_min=math.inf;spread_max=-math.inf;spread_sample=[];spread_sample_cap=200000;abnormal_spread=0
    jumps=[];gaps=[];daily=defaultdict(lambda:Counter());weekday=Counter();max_jump=0.0
    for rec,path in decoded_files:
        source_rel=rec['source_bi5_path']
        with gzip.open(path,'rt',newline='',encoding='utf-8') as fh:
            rd=csv.DictReader(fh)
            for row in rd:
                total+=1;ts=parse_ts(row['timestamp_utc']);bid=float(row['bid']);ask=float(row['ask']);spread=ask-bid;spips=spread/PIP_SIZE
                if first_ts is None:first_ts=ts
                last_ts=ts
                if prev_ts is not None:
                    if ts<prev_ts:out_of_order+=1
                    if ts==prev_ts:dup_ts+=1
                    d=(ts-prev_ts).total_seconds()
                    if d>900:
                        cls=classify_gap(prev_ts,ts);gaps.append({'previous_timestamp_utc':fmt_ts(prev_ts),'next_timestamp_utc':fmt_ts(ts),'gap_seconds':int(d),'gap_hours':round(d/3600,6),'previous_weekday':prev_ts.strftime('%A'),'next_weekday':ts.strftime('%A'),'classification':cls,'critical':cls=='UNEXPLAINED_INTRAWEEK_GAP' and d>=7200})
                tup=(row['timestamp_utc'],row['bid'],row['ask'],row.get('bid_volume',''),row.get('ask_volume',''))
                if tup==prev_row:dup_row+=1
                if not row['bid']:missing_bid+=1
                if not row['ask']:missing_ask+=1
                if ask<bid:ask_lt_bid+=1
                if spread==0:zero_spread+=1
                if spread<0:negative_spread+=1
                if bid<=0 or ask<=0:zero_price+=1
                if ts.weekday()>=5:weekend_ticks+=1
                if prev_row is not None:
                    jump=abs(bid-float(prev_row[1]))/PIP_SIZE;max_jump=max(max_jump,jump)
                    if jump>50:jumps.append({'timestamp_utc':fmt_ts(ts),'jump_pips':round(jump,6),'previous_bid':prev_row[1],'bid':row['bid']})
                if spips>10:abnormal_spread+=1
                spread_sum+=spips;spread_min=min(spread_min,spips);spread_max=max(spread_max,spips)
                if len(spread_sample)<spread_sample_cap:spread_sample.append(spips)
                elif total%97==0:spread_sample[(total//97)%spread_sample_cap]=spips
                day=ts.date().isoformat();daily[day]['ticks']+=1;daily[day]['zero_spread']+=spread==0;daily[day]['negative_spread']+=spread<0;daily[day]['weekend_ticks']+=ts.weekday()>=5;weekday[ts.strftime('%A')]+=1
                w.writerow({'timestamp_utc':fmt_ts(ts),'bid':f'{bid:.8f}','ask':f'{ask:.8f}','spread_price':f'{spread:.8f}','spread_pips':f'{spips:.8f}','symbol':SYMBOL,'source':SOURCE,'source_file':source_rel,'year':y,'month':m,'trading_date_utc':day,'sequence':total})
                bars.add(ts,bid,ask);prev_ts=ts;prev_row=tup
    f.close()
    with raw_csv.open('rb') as i,normalized.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=9) as gz:
            for b in iter(lambda:i.read(1024*1024),b''):gz.write(b)
    raw_csv.unlink();bar_receipt=bars.close()
    expected_rows=sum(int(r.get('rows',0)) for r in downloaded);bar_consistency=all(v['tick_count_sum']==total for v in bar_receipt.values())
    day_path=qc/'tick_quality_by_day.csv'
    with day_path.open('w',newline='',encoding='utf-8') as fh:
        wr=csv.writer(fh,lineterminator='\n');wr.writerow(['trading_date_utc','weekday','tick_count','zero_spread','negative_spread','weekend_ticks'])
        for day,c in sorted(daily.items()):wr.writerow([day,dt.date.fromisoformat(day).strftime('%A'),c['ticks'],c['zero_spread'],c['negative_spread'],c['weekend_ticks']])
    gap_path=qc/'gap_catalog.csv'
    with gap_path.open('w',newline='',encoding='utf-8') as fh:
        cols=['previous_timestamp_utc','next_timestamp_utc','gap_seconds','gap_hours','previous_weekday','next_weekday','classification','critical'];wr=csv.DictWriter(fh,fieldnames=cols,lineterminator='\n');wr.writeheader();wr.writerows(gaps)
    jump_path=qc/'price_jump_catalog.csv'
    with jump_path.open('w',newline='',encoding='utf-8') as fh:
        cols=['timestamp_utc','jump_pips','previous_bid','bid'];wr=csv.DictWriter(fh,fieldnames=cols,lineterminator='\n');wr.writeheader();wr.writerows(jumps)
    spread={'year':y,'month':m,'tick_count':total,'min_spread_pips':None if total==0 else spread_min,'max_spread_pips':None if total==0 else spread_max,'mean_spread_pips':None if total==0 else spread_sum/total,'p50_spread_pips_approx':percentile(spread_sample,.5),'p90_spread_pips_approx':percentile(spread_sample,.9),'p95_spread_pips_approx':percentile(spread_sample,.95),'p99_spread_pips_approx':percentile(spread_sample,.99),'p999_spread_pips_approx':percentile(spread_sample,.999),'abnormal_threshold_pips':10.0,'abnormal_spread_count':abnormal_spread,'sample_size':len(spread_sample)}
    write_json(qc/'spread_distribution.json',spread)
    summary=json.loads(Path(args.download_summary).read_text(encoding='utf-8'))
    critical=sum(1 for g in gaps if g['critical'])
    quality={'schema_version':'usdjpy_tick_authority_month_quality_v1','work_id':WORK_ID,'year':y,'month':m,'period_role':role,'source':SOURCE,'expected_hours':summary['expected_hours'],'resolved_hours':summary['resolved_hours'],'downloaded_hours':summary['downloaded_hours'],'missing_404_hours':summary['missing_404_hours'],'no_tick_hours':summary['no_tick_hours'],'error_hours':summary['error_hours'],'download_retry_attempts':max(0,len(attempts)-summary['expected_hours']),'source_file_missing_count':len(missing_source),'tick_count':total,'first_timestamp_utc':fmt_ts(first_ts) if first_ts else None,'last_timestamp_utc':fmt_ts(last_ts) if last_ts else None,'timestamp_monotonic_non_decreasing':out_of_order==0,'out_of_order_count':out_of_order,'duplicate_timestamp_count':dup_ts,'complete_duplicate_row_count':dup_row,'bid_missing_count':missing_bid,'ask_missing_count':missing_ask,'ask_less_than_bid_count':ask_lt_bid,'zero_spread_count':zero_spread,'negative_spread_count':negative_spread,'zero_or_negative_price_count':zero_price,'abnormal_spread_count':abnormal_spread,'price_jump_over_50_pips_count':len(jumps),'max_consecutive_bid_jump_pips':max_jump,'gap_over_15m_count':len(gaps),'critical_gap_count':critical,'weekend_tick_count':weekend_ticks,'weekday_coverage':dict(weekday),'raw_to_normalized_rows_match':expected_rows==total,'normalized_to_bar_tick_counts_match':bar_consistency,'leap_day_tick_count':daily.get('2020-02-29',{}).get('ticks',0) if y==2020 and m==2 else None,'month_boundary_audit':'DEFERRED_TO_ROOT_AGGREGATION','dst_contract':'UTC_SOURCE_NATIVE_NO_TIMESTAMP_SHIFT','bar_receipt':bar_receipt}
    write_json(qc/'tick_quality_summary.json',quality)
    raw_asset=assets/f'USDJPY_DUKASCOPY_RAW_BI5_{y}_{m:02d}.tar.gz';raw_paths=[p for p in (root/'source_bi5').rglob('*') if p.is_file()]+[Path(args.download_manifest),Path(args.download_summary)]
    deterministic_tar_gz(raw_asset,Path(args.download_root).parent,raw_paths)
    bars_asset=assets/f'USDJPY_DUKASCOPY_BARS_{y}_{m:02d}.tar.gz';deterministic_tar_gz(bars_asset,out,[p for p in bars_root.rglob('*') if p.is_file()])
    qc_asset=assets/f'USDJPY_DUKASCOPY_QC_{y}_{m:02d}.tar.gz';deterministic_tar_gz(qc_asset,out,[p for p in qc.rglob('*') if p.is_file()])
    payloads=[]
    for layer,p in [('raw',raw_asset),('normalized',normalized),('bars',bars_asset),('quality',qc_asset)]:payloads.append({'layer':layer,'name':p.name,'path':p.as_posix(),'bytes':p.stat().st_size,'sha256':sha256_file(p)})
    decision='FAIL_SCHEMA_OR_PRICE_INTEGRITY' if any([missing_source,summary['error_hours'],ask_lt_bid,negative_spread,zero_price,out_of_order,expected_rows!=total,not bar_consistency]) else ('PASS_WITH_DOCUMENTED_SOURCE_GAPS' if critical else 'PASS_2020_2022_TICK_AUTHORITY_CERTIFIED')
    receipt={'schema_version':'usdjpy_tick_authority_month_receipt_v1','work_id':WORK_ID,'source_sha':args.source_sha,'year':y,'month':m,'period_role':role,'decision':decision,'quality':quality,'spread_distribution':spread,'assets':payloads,'production_authorization':False,'candidate_evaluation_executed':False,'strategy_scoring_executed':False,'remote_release_assets':[]}
    write_json(out/f'USDJPY_DUKASCOPY_RECEIPT_{y}_{m:02d}.json',receipt)
    print(json.dumps({'year':y,'month':m,'decision':decision,'ticks':total,'critical_gaps':critical,'assets':len(payloads)},sort_keys=True))

if __name__=='__main__':main()
