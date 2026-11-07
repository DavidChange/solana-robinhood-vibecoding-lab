"""V9.3: token discovery, narrative watchlist, explicit evidence, PAPER-TRADING ONLY.
No signing, wallet, seed phrases, or blockchain order submission.
"""
import os, subprocess, threading, sys, argparse, datetime as dt, html, json, math, re, sqlite3, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET, email.utils
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'dados'; DB=DATA/'v93.sqlite'; PANEL=ROOT/'PAINEL_V93.html'; WATCH=ROOT/'narrativas.json'
TZ=ZoneInfo('America/Sao_Paulo')
CHAINS={'solana':'Solana','robinhood':'Robinhood Chain'}
BASE='https://api.dexscreener.com'
CAPITAL=1000.0; MAX_MC=30000.; MAX_COST=25.; FEE=.003; SLIP=.02; STOP=-.10; TAKE_NET=100.; MAX_AGE=3600
MAX_POOL_AGE_MINUTES=180; MAX_ENTRY_SHARE_OF_LIQ=0.005; MAX_EXIT_SHARE_OF_LIQ=0.05; MIN_LIQUIDITY=3000; NEWS_INTERVAL=900; MAX_NEWS_TOPICS=5

def fmt(ts): return dt.datetime.fromtimestamp(ts,dt.timezone.utc).astimezone(TZ).strftime('%d/%m/%Y %H:%M:%S') if ts else '—'
def money(v):return '—' if v is None else f'US$ {v:,.2f}'
def n(v):
    try:
        x=float(v);return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None
def http(url,headers=None):
    req=urllib.request.Request(url,headers={'User-Agent':'V9ResearchBot/1.0',**(headers or {})})
    with urllib.request.urlopen(req,timeout=12) as r:return json.load(r)
def safe_url(u):
    if not isinstance(u,str):return ''
    p=urllib.parse.urlparse(u)
    return u if p.scheme=='https' and p.netloc and not p.username and not p.password else ''
def h(v):return html.escape(str(v if v is not None else '—'),quote=True)
def link(url,title): return f'<a href="{h(url)}" target="_blank" rel="noopener noreferrer">{h(title)}</a>' if safe_url(url) else h(title)

def conn(path=DB):
    path.parent.mkdir(exist_ok=True,parents=True)
    c=sqlite3.connect(path);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL')
    c.executescript('''CREATE TABLE IF NOT EXISTS tokens(chain TEXT,mint TEXT,symbol TEXT,name TEXT,first_seen REAL,last_seen REAL,price REAL,mc REAL,fdv REAL,liquidity REAL,buys INTEGER,sells INTEGER,url TEXT,description TEXT,x_url TEXT,website TEXT,age_minutes REAL,source TEXT,PRIMARY KEY(chain,mint));
    CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY,ts REAL,chain TEXT,mint TEXT,price REAL,mc REAL,fdv REAL,liquidity REAL);
    CREATE INDEX IF NOT EXISTS oi ON observations(chain,mint,ts);
    CREATE TABLE IF NOT EXISTS narratives(id TEXT PRIMARY KEY,title TEXT,keywords TEXT,source_url TEXT,source_time REAL,observed_time REAL,source_type TEXT,verified INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS matches(narrative_id TEXT,chain TEXT,mint TEXT,matched_at REAL,reason TEXT,relation TEXT,PRIMARY KEY(narrative_id,chain,mint));
    CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY,chain TEXT,mint TEXT,symbol TEXT,entry_ts REAL,entry_price REAL,entry_mc REAL,cost REAL,qty REAL,status TEXT,exit_ts REAL,exit_price REAL,exit_mc REAL,pnl REAL,reason TEXT);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,level TEXT,message TEXT);
    CREATE TABLE IF NOT EXISTS execution_quotes(id INTEGER PRIMARY KEY,trade_id INTEGER,ts REAL,chain TEXT,mint TEXT,stage TEXT,price REAL,mc REAL,liquidity REAL,source TEXT,eligible INTEGER,notes TEXT);
    CREATE INDEX IF NOT EXISTS ix_exec_trade ON execution_quotes(trade_id,ts);
    CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY, ts REAL, trade_id INTEGER, kind TEXT, title TEXT, body TEXT, UNIQUE(trade_id,kind));
    CREATE TABLE IF NOT EXISTS risk_flags(chain TEXT, mint TEXT,ts REAL, level TEXT, flags TEXT, PRIMARY KEY(chain,mint));
    CREATE TABLE IF NOT EXISTS account(id INTEGER PRIMARY KEY CHECK(id=1),cash REAL);
    INSERT OR IGNORE INTO account VALUES(1,1000.0);''')
    c.commit();return c

def load_watch():
    if not WATCH.exists():WATCH.write_text('[]\n',encoding='utf-8')
    obj=json.loads(WATCH.read_text(encoding='utf-8'))
    return obj if isinstance(obj,list) else []

def ingest_watch(c,now):
    for item in load_watch():
        if not isinstance(item,dict) or not str(item.get('id','')).strip():continue
        title=str(item.get('title',''))[:160];keys=item.get('keywords',[])
        if not isinstance(keys,list):keys=[]
        url=safe_url(item.get('source_url',''))
        st=n(item.get('published_unix'))
        c.execute('INSERT OR IGNORE INTO narratives(id,title,keywords,source_url,source_time,observed_time,source_type,verified) VALUES(?,?,?,?,?,?,?,?)',
                  (str(item['id'])[:80],title,json.dumps([str(k)[:70] for k in keys[:12]]),url,st,now,'MANUAL',0))

def ingest_free_news(c,now):
    """Optional free public Google News RSS feeds for USER-SUPPLIED watchlist topics.
    Records the publication time and first observation separately. No X API access.
    RSS availability/terms may change; failures should not stop scanning.
    """
    topics=[]
    for item in load_watch():
        if not isinstance(item,dict) or not item.get('rss_enabled',False):continue
        keys=item.get('keywords',[])
        if isinstance(keys,list):
            for term in keys[:1]:
                term=str(term).strip()
                if 3 <= len(term) <= 70:topics.append(term)
    added=0
    for topic in topics[:MAX_NEWS_TOPICS]:
        url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':topic+' when:1d','hl':'en-US','gl':'US','ceid':'US:en'})
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 V92PersonalResearch/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw=resp.read(300000)
            root=ET.fromstring(raw)
        except Exception as e:
            raise RuntimeError('RSS indisponivel ('+topic[:30]+'): '+type(e).__name__) from e
        for entry in root.findall('./channel/item')[:15]:
            title=(entry.findtext('title') or '').strip()[:160]
            link_url=safe_url((entry.findtext('link') or '').strip())
            guid=(entry.findtext('guid') or link_url)
            if not title or not link_url:continue
            pub=None
            try:
                parsed=email.utils.parsedate_to_datetime(entry.findtext('pubDate') or '')
                pub=parsed.timestamp()
            except (TypeError,ValueError,OverflowError):pass
            import hashlib
            uid='rss_'+hashlib.sha256(guid.encode('utf-8')).hexdigest()[:26]
            kw=[topic]
            exists=c.execute('SELECT 1 FROM narratives WHERE id=?',(uid,)).fetchone()
            c.execute('INSERT OR IGNORE INTO narratives(id,title,keywords,source_url,source_time,observed_time,source_type,verified) VALUES(?,?,?,?,?,?,?,0)',(uid,title,json.dumps(kw),link_url,pub,now,'RSS_NAO_VERIFICADO'))
            if not exists:added+=1
    return added

def candidate_addresses(items):
    out={'solana':[], 'robinhood':[]};metadata={}
    for x in items:
        if not isinstance(x,dict):continue
        ch=str(x.get('chainId','')).lower(); addr=x.get('tokenAddress')
        if ch in out and isinstance(addr,str) and addr not in out[ch]:
            out[ch].append(addr);metadata[(ch,addr)]=x
    return out,metadata

def fetch_open_positions(c):
    errors=[];found=[]
    for row in c.execute("SELECT chain,mint FROM trades WHERE status='OPEN'"):
        ch,mint=row['chain'],row['mint']
        try:
            result=http(BASE+'/tokens/v1/'+ch+'/'+urllib.parse.quote(mint,safe=''))
            if isinstance(result,list):found.extend(result)
        except Exception as e:errors.append(f'posicao {ch}: {type(e).__name__}: {str(e)[:100]}')
    return found,errors

def discover():
    errors=[];raw=[]
    for ep in ('/token-profiles/latest/v1','/token-boosts/latest/v1','/community-takeovers/latest/v1'):
        try:
            data=http(BASE+ep)
            if isinstance(data,list):raw+=data
        except Exception as e:errors.append(f'{ep}: {type(e).__name__}: {str(e)[:130]}')
    addresses,meta=candidate_addresses(raw);pairs=[]
    for ch,addrs in addresses.items():
        for i in range(0,min(len(addrs),120),30):
            try:
                data=http(BASE+'/tokens/v1/'+ch+'/'+','.join(addrs[i:i+30]))
                if isinstance(data,list):pairs+=data
            except Exception as e:errors.append(f'{ch} pairs: {type(e).__name__}: {str(e)[:130]}')
    return pairs,meta,errors, {k:len(v) for k,v in addresses.items()}

def social(p,meta):
    info=p.get('info') or {};m=meta or {};urls=[]
    for x in info.get('socials') or []:
        u=x.get('url')
        if not u and x.get('handle') and str(x.get('platform','')).lower() in ('twitter','x'):
            u='https://x.com/'+str(x['handle']).lstrip('@')
        if u:urls.append(u)
    for x in m.get('links') or []:
        if isinstance(x,dict):urls.append(x.get('url',''))
    x_url=next((u for u in urls if safe_url(u) and urllib.parse.urlparse(u).hostname in ('x.com','twitter.com','www.x.com','www.twitter.com')), '')
    sites=[x.get('url','') for x in info.get('websites') or [] if isinstance(x,dict)]
    website=next((safe_url(u) for u in sites if safe_url(u)), '')
    return x_url,website

def normalize(p,meta):
    ch=str(p.get('chainId','')).lower();base=p.get('baseToken') or {};mint=base.get('address');price=n(p.get('priceUsd'));mc=n(p.get('marketCap'))
    if ch not in CHAINS or not mint or not price or price<=0:return None
    # MC must be provided independently, never replace with FDV.
    if mc is None or mc<=0 or mc>MAX_MC:return None
    liq=n((p.get('liquidity') or {}).get('usd'))
    tx=(p.get('txns') or {}).get('m5') or {}
    x_url,website=social(p,meta)
    created=n(p.get('pairCreatedAt'));age=max(0,(time.time()-created/1000)/60) if created else None
    return dict(chain=ch,mint=mint,symbol=str(base.get('symbol') or '?')[:45],name=str(base.get('name') or '')[:120],price=price,mc=mc,fdv=n(p.get('fdv')),liquidity=liq,buys=int(n(tx.get('buys')) or 0),sells=int(n(tx.get('sells')) or 0),url=safe_url(p.get('url','')),description=str((meta or {}).get('description') or '')[:900],x_url=x_url,website=website,age_minutes=age,source='DEXSCREENER_PUBLIC_SAMPLE')

def narrative_match(c,tok,now):
    text=' '.join((tok['symbol'],tok['name'],tok['description'])).lower()
    for r in c.execute('SELECT * FROM narratives'):
        try:kw=json.loads(r['keywords'])
        except (TypeError,ValueError):continue
        matched=[k for k in kw if isinstance(k,str) and len(k.strip())>=4 and k.strip().lower() in text]
        if not matched:continue
        relation=('PUBLICACAO_ANTERIOR_A_DETECCAO' if r['source_time'] and r['source_time'] < now else 'HORARIO_NAO_CONFIRMADO')
        # First recorded discovery is not necessarily token creation. No official association is inferred.
        c.execute('INSERT OR IGNORE INTO matches VALUES(?,?,?,?,?,?)',(r['id'],tok['chain'],tok['mint'],now,'Palavra(s): '+', '.join(matched[:4]),relation))

def execution_observation(c,pos,now,t,stage,eligible,notes):
    c.execute('''INSERT INTO execution_quotes(trade_id,ts,chain,mint,stage,price,mc,liquidity,source,eligible,notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
              (pos['id'],now,pos['chain'],pos['mint'],stage,t.get('price'),t.get('mc'),t.get('liquidity'),t.get('source','DEXSCREENER_API'),int(eligible),notes))
    # Every quote used to value a trade is also added to the observations history.
    if t.get('price') and t['price'] > 0:
        c.execute('INSERT INTO observations(ts,chain,mint,price,mc,fdv,liquidity) VALUES(?,?,?,?,?,?,?)',
                  (now,pos['chain'],pos['mint'],t['price'],t.get('mc'),t.get('fdv'),t.get('liquidity')))

def risk_assessment(t):
    """Informational heuristics only; not contract audit or proof of bots/fraud."""
    flags=[]
    liq=t.get('liquidity')
    if liq is None or liq<=0:flags.append('LIQUIDEZ NAO VERIFICADA')
    elif liq<5000:flags.append('LIQUIDEZ BAIXA')
    if t.get('age_minutes') is None:flags.append('IDADE DESCONHECIDA')
    elif t['age_minutes']<5:flags.append('POOL MUITO NOVO')
    total=t['buys']+t['sells']
    if total>=100:flags.append('ATIVIDADE INTENSA; BOTS NAO VERIFICADOS')
    if not t.get('website') and not t.get('x_url'):flags.append('SEM LINKS SOCIAIS')
    if liq and t['mc']>0 and liq/t['mc']<.08:flags.append('BAIXA RELACAO LIQUIDEZ/MC')
    level='ATENCAO' if flags else 'NAO AUDITADO'
    if liq is None or liq<5000:level='DADOS INSUFICIENTES'
    return level,flags

def record_notification(c, now, trade_id, kind, title, body):
    c.execute('INSERT OR IGNORE INTO notifications(ts,trade_id,kind,title,body) VALUES(?,?,?,?,?)',
              (now,trade_id,kind,title,body))

def notify_windows(title, message, sound=True):
    """Local Windows balloon notification. No network, no external dependencies."""
    if os.name!='nt':return
    if sound:
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:pass
    # Send text to a PowerShell child process through stdin (avoid command injection).
    ps=("Add-Type -AssemblyName System.Windows.Forms; "
        "$obj=New-Object System.Windows.Forms.NotifyIcon; "
        "$obj.Icon=[System.Drawing.SystemIcons]::Information; "
        "$obj.Visible=$true; "
        "$obj.BalloonTipTitle=[Console]::ReadLine(); "
        "$obj.BalloonTipText=[Console]::ReadLine(); "
        "$obj.ShowBalloonTip(6000); Start-Sleep -Seconds 7; $obj.Dispose()")
    try:
        subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-WindowStyle','Hidden','-Command',ps],
            stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).communicate(
                (title[:63].replace('\n',' ')+'\n'+message[:240].replace('\n',' ')+'\n').encode('utf-8'),timeout=12)
    except Exception:pass

def notification_worker(db_path,stop_event):
    # separate read-only DB connection; only consume notifications created after startup
    try:
        nc=sqlite3.connect(db_path,timeout=8)
        last=nc.execute('SELECT COALESCE(MAX(id),0) FROM notifications').fetchone()[0]
        nc.close()
    except sqlite3.Error:return
    while not stop_event.wait(2):
        try:
            nc=sqlite3.connect(db_path,timeout=8)
            rows=nc.execute('SELECT id,title,body FROM notifications WHERE id>? ORDER BY id LIMIT 20',(last,)).fetchall()
            nc.close()
            for row in rows:
                last=row[0]
                notify_windows(row[1],row[2])
        except sqlite3.Error:continue

def open_trade(c,t,now):
    if t['liquidity'] is None or t['liquidity']<5000 or t['mc']<1000 or t['age_minutes'] is None or t['age_minutes']>30:return
    if t['buys']<5 or t['buys']<=t['sells']:return
    if not t['x_url'] and not c.execute('SELECT 1 FROM matches WHERE chain=? AND mint=?',(t['chain'],t['mint'])).fetchone():return
    if c.execute("SELECT 1 FROM trades WHERE status='OPEN'").fetchone():return
    if c.execute('SELECT 1 FROM trades WHERE chain=? AND mint=?',(t['chain'],t['mint'])).fetchone():return
    cash=c.execute('SELECT cash FROM account').fetchone()[0]
    cost=min(MAX_COST,t['liquidity']*MAX_ENTRY_SHARE_OF_LIQ,cash)
    if cost<2:return
    qty=(cost/(1+FEE))/(t['price']*(1+SLIP))
    cur=c.execute("INSERT INTO trades(chain,mint,symbol,entry_ts,entry_price,entry_mc,cost,qty,status) VALUES(?,?,?,?,?,?,?,?, 'OPEN')",
             (t['chain'],t['mint'],t['symbol'],now,t['price'],t['mc'],cost,qty))
    c.execute('UPDATE account SET cash=cash-?',(cost,))
    pos={'id':cur.lastrowid,'chain':t['chain'],'mint':t['mint']}
    execution_observation(c,pos,now,t,'ENTRY',True,'Taxa 0,3%; slippage estimado 2%')
    record_notification(c,now,cur.lastrowid,'ENTRY','V9.3 | COMPRA FICTICIA',
                        f'{t["symbol"]} ({CHAINS[t["chain"]]}) | US$ {cost:.2f} | MC US$ {t["mc"]:,.0f} | {fmt(now)} BRT')

def close_trades(c,latest,now):
    for pos in c.execute("SELECT * FROM trades WHERE status='OPEN'").fetchall():
        t=latest.get((pos['chain'],pos['mint']))
        if not t:continue
        price=t.get('price');liq=t.get('liquidity')
        valid=price is not None and math.isfinite(price) and price>0 and liq is not None and liq>=5000
        # Reject overstated paper profits when simulated sell proceeds are a large portion of quoted liquidity.
        proceeds=pos['qty']*price*(1-SLIP)*(1-FEE) if price and price>0 else None
        if proceeds is not None and liq is not None and proceeds>liq*MAX_EXIT_SHARE_OF_LIQ:valid=False
        pnl=proceeds-pos['cost'] if proceeds is not None else None
        move=price/pos['entry_price']-1 if price and price>0 else None
        age=now-pos['entry_ts']
        why=('STOP_OBSERVADO' if move is not None and move<=STOP else
             'ALVO_LIQUIDO_100' if pnl is not None and pnl>=TAKE_NET else
             'TEMPO_60_MIN' if age>=MAX_AGE else None)
        note=('Dados insuficientes: sem liquidez >= US$ 5.000' if not valid else 'Cotacao aceita no modelo fixo; swap real nao validado')
        execution_observation(c,pos,now,t,'EXIT_ATTEMPT' if why else 'MONITOR',valid,note)
        if why and not valid:
            c.execute('INSERT INTO events(ts,level,message) VALUES(?,?,?)',(now,'WARN',f'EXIT BLOQUEADA {pos["symbol"]}: {note}; posicao ainda aberta'))
            continue
        if why and valid:
            c.execute("UPDATE trades SET status='CLOSED',exit_ts=?,exit_price=?,exit_mc=?,pnl=?,reason=? WHERE id=?",
                      (now,price,t.get('mc'),pnl,why,pos['id']))
            c.execute('UPDATE account SET cash=cash+?',(proceeds,))
            record_notification(c,now,pos['id'],'EXIT','V9.3 | SAIDA FICTICIA',
                                f'{pos["symbol"]}: {why} | P&L US$ {pnl:+.2f} | {fmt(now)} BRT')

def tick(c,pairs,meta,now,position_pairs=None):
    chosen={}
    for p in pairs:
        ch=str(p.get('chainId','')).lower();mint=(p.get('baseToken') or {}).get('address')
        t=normalize(p,meta.get((ch,mint)))
        if t and ((ch,mint) not in chosen or (t['liquidity'] or 0)>(chosen[(ch,mint)]['liquidity'] or 0)):chosen[ch,mint]=t
    with c:
        for t in chosen.values():
            key=(t['chain'],t['mint']);old=c.execute('SELECT first_seen FROM tokens WHERE chain=? AND mint=?',key).fetchone()
            c.execute('''INSERT INTO tokens(chain,mint,symbol,name,first_seen,last_seen,price,mc,fdv,liquidity,buys,sells,url,description,x_url,website,age_minutes,source)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(chain,mint) DO UPDATE SET symbol=excluded.symbol,name=excluded.name,last_seen=excluded.last_seen,price=excluded.price,mc=excluded.mc,fdv=excluded.fdv,liquidity=excluded.liquidity,buys=excluded.buys,sells=excluded.sells,url=excluded.url,description=excluded.description,x_url=excluded.x_url,website=excluded.website,age_minutes=excluded.age_minutes''',
                (t['chain'],t['mint'],t['symbol'],t['name'],old['first_seen'] if old else now,now,t['price'],t['mc'],t['fdv'],t['liquidity'],t['buys'],t['sells'],t['url'],t['description'],t['x_url'],t['website'],t['age_minutes'],t['source']))
            c.execute('INSERT INTO observations(ts,chain,mint,price,mc,fdv,liquidity) VALUES(?,?,?,?,?,?,?)',(now,*key,t['price'],t['mc'],t['fdv'],t['liquidity']))
            narrative_match(c,t,now)
            level,flags=risk_assessment(t)
            c.execute('''INSERT INTO risk_flags(chain,mint,ts,level,flags) VALUES(?,?,?,?,?)
                         ON CONFLICT(chain,mint) DO UPDATE SET ts=excluded.ts,level=excluded.level,flags=excluded.flags''',
                      (t['chain'],t['mint'],now,level,json.dumps(flags,ensure_ascii=False)))
        quotes=dict(chosen)
        for p in position_pairs or []:
            ch=str(p.get('chainId','')).lower();mint=(p.get('baseToken') or {}).get('address')
            if ch not in CHAINS or not mint:continue
            price=n(p.get('priceUsd'))
            if price is None or price<=0:continue
            liq=n((p.get('liquidity') or {}).get('usd'))
            key=(ch,mint)
            if key not in quotes or (liq or 0)>(quotes[key]['liquidity'] or 0):
                quotes[key]={'chain':ch,'mint':mint,'price':price,'mc':n(p.get('marketCap')),'fdv':n(p.get('fdv')),'liquidity':liq,'source':'DEXSCREENER_POSITION_LOOKUP'}
        close_trades(c,quotes,now)
        for t in chosen.values():open_trade(c,t,now)
    return len(chosen)

def dashboard(c,now,health='Aguardando primeira coleta'):
    def table(headers,rows):
        return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+h(v)+'</th>' for v in headers)+'</tr></thead><tbody>'+(''.join(rows) or f'<tr><td colspan="{len(headers)}">Nenhum registro disponível.</td></tr>')+'</tbody></table></div>'
    tok=[]
    for t in c.execute('SELECT * FROM tokens ORDER BY first_seen DESC LIMIT 100'):
        matches=c.execute('SELECT count(*) FROM matches WHERE chain=? AND mint=?',(t['chain'],t['mint'])).fetchone()[0]
        symbol=link(t['url'],t['symbol']);url=link(t['x_url'],'Ver X') if t['x_url'] else '—';website=link(t['website'],'Site') if t['website'] else '—'
        age='Desconhecida' if t['age_minutes'] is None else f'{t["age_minutes"]:.0f} min'
        risk=c.execute('SELECT level,flags FROM risk_flags WHERE chain=? AND mint=?',(t['chain'],t['mint'])).fetchone()
        liq_status=(h(risk['level'])+' <span class="muted" title="'+h('; '.join(json.loads(risk['flags'])))+'">ⓘ</span>') if risk else 'NÃO AUDITADO'
        tok.append('<tr>'+''.join(f'<td>{v}</td>' for v in (h(CHAINS[t['chain']]),symbol,h(fmt(t['first_seen'])),h(money(t['mc'])),h(money(t['fdv'])),h(money(t['liquidity'])),h(t['buys']),h(t['sells']),h(age),url,website,h(matches),liq_status))+'</tr>')
    nr=[]
    for r in c.execute('SELECT * FROM narratives ORDER BY observed_time DESC LIMIT 100'):
        m=c.execute('SELECT count(*) FROM matches WHERE narrative_id=?',(r['id'],)).fetchone()[0]
        nr.append('<tr>'+''.join(f'<td>{v}</td>' for v in (link(r['source_url'],r['title']),h(r['source_type']),h(fmt(r['source_time'])),h(fmt(r['observed_time'])),h(m),'Não verificada (palavras)'))+'</tr>')
    mt=[]
    for r in c.execute('SELECT m.*,t.symbol,t.url,n.source_time,n.source_url FROM matches m JOIN tokens t ON m.chain=t.chain AND m.mint=t.mint JOIN narratives n ON n.id=m.narrative_id ORDER BY m.matched_at DESC LIMIT 100'):
        mt.append('<tr>'+''.join(f'<td>{v}</td>' for v in (h(CHAINS[r['chain']]),link(r['url'],r['symbol']),link(r['source_url'],r['narrative_id']),h(r['reason']),h(r['relation'])))+'</tr>')
    attempts=[]
    for q in c.execute('SELECT * FROM execution_quotes ORDER BY id DESC LIMIT 100'):
        attempts.append('<tr>'+''.join(f'<td>{v}</td>' for v in
            (h(q['trade_id']),h(fmt(q['ts'])),h(q['chain']),h(q['stage']),h(money(q['mc'])),h(money(q['liquidity'])),h(q['source']),h('SIM' if q['eligible'] else 'NÃO'),h(q['notes'])))+'</tr>')
    tr=[]
    for r in c.execute('SELECT * FROM trades ORDER BY id DESC LIMIT 100'):
        pnl=h(money(r['pnl'])) if r['pnl'] is not None else 'Aberta'
        urlrow=c.execute('SELECT url FROM tokens WHERE chain=? AND mint=?',(r['chain'],r['mint'])).fetchone()
        dex_link=link(urlrow['url'],r['symbol']) if urlrow else h(r['symbol'])
        tr.append('<tr>'+''.join(f'<td>{v}</td>' for v in (h(CHAINS[r['chain']]),dex_link,h(fmt(r['entry_ts'])),h(money(r['entry_mc'])),h(money(r['cost'])),h(r['status']),h(money(r['exit_mc'])),pnl,h(r['reason'] or '—')) )+'</tr>')
    css=''':root{color-scheme:dark}*{box-sizing:border-box}body{background:radial-gradient(circle at 10% 0%,#2f1558 0%,#100c21 48%,#0d0b19 100%);color:#f0eaff;font:14px Segoe UI,Arial,sans-serif;margin:0}main{margin:auto;max-width:1660px;padding:28px 26px 54px}h1{margin-bottom:7px;font-size:29px;color:#f5e8ff}h2{margin:32px 0 15px;color:#e5c9ff}p{color:#cbbadd}.summary{background:#211636;border:1px solid #503376;border-radius:15px;padding:17px;line-height:1.8}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:13px;margin:21px 0}.metric{background:linear-gradient(140deg,#35204f,#241839);border:1px solid #543678;padding:19px;border-radius:14px}.metric b{display:block;font-size:24px;margin-top:9px;color:#fff}.scroll{overflow-x:auto;border:1px solid #503376;border-radius:13px}table{border-collapse:collapse;min-width:900px;width:100%;background:#20172f}th,td{border-bottom:1px solid #48345f;padding:12px 11px;white-space:nowrap;text-align:left}th{background:#3d245b;color:#f3defe}tr:hover td{background:#342049}a{color:#c7a2ff;text-decoration:underline;text-underline-offset:3px}small{color:#bca9cf}.warn{color:#ffd38a}details{background:#211636;border:1px solid #503376;padding:16px;border-radius:12px}summary{cursor:pointer}.muted{color:#a99abb}.up{color:#64e9b9}.down{color:#ff8eaf}.tag{display:inline-block;padding:5px 9px;border-radius:99px;background:#473067;color:#eacaff;font-size:12px;margin-left:6px}.logo{color:#cdadff}::selection{background:#7f48c8}'''
    cash=c.execute('SELECT cash FROM account').fetchone()[0]
    closed=c.execute("SELECT COALESCE(sum(pnl),0) FROM trades WHERE status='CLOSED'").fetchone()[0]
    htmlpage=f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta http-equiv="refresh" content="30"><title>Solana + Robinhood V9.3</title><style>{css}</style></head><body><main><h1>Bot V9.3 — Narrativas e microcaps (sem API paga)</h1><p>Brasília · {h(fmt(now))} · Ordens reais: DESATIVADAS</p><div class="metrics"><div class="metric">Banca fictícia<b>US$ 1.000</b></div><div class="metric">Dinheiro livre<b>{h(money(cash))}</b></div><div class="metric">P&L realizado<b>{h(money(closed))}</b></div><div class="metric">Tokens elegíveis observados<b>{c.execute('SELECT count(*) FROM tokens').fetchone()[0]}</b></div><div class="metric">Narrativas monitoradas<b>{c.execute('SELECT count(*) FROM narratives').fetchone()[0]}</b></div></div><div class="summary"><strong>Estado:</strong> {h(health)}<br><strong>Cobertura:</strong> amostra de perfis/boosts/takeovers DEX Screener, não feed completo de lançamentos on-chain. Robinhood Chain pode não aparecer na amostra. Consultas pagas ao X permanentemente desabilitadas nesta versão. Alertas no Windows com som dependem de permissões de notificações do sistema. Links sociais não significam posts analisados. RSS público opcional para temas cadastrados; RSS pode falhar ou mudar.<br><strong>Segurança:</strong> não há auditoria abrangente de rug pull, honeypot ou bots nesta versão. Simulação bloqueada sem liquidez mínima; tentativa de saída sem dados fica pendente e é auditada. Não habilitar ordens reais com estes filtros.</div><details open><summary>Como funciona o contexto e o score?</summary><p>Não há score de previsão por IA nesta versão. O painel mostra idade aproximada do pool (não do token). A fonte pode não informar idade ou liquidez. Entrada fictícia requer idade conhecida de até 30 minutos, liquidez >= US$ 5 mil e os filtros já existentes. A associação narrativa-token é <strong>heurística por palavras</strong> e não comprova relação oficial. "Anterior" só indica que o horário publicado foi informado como anterior à identificação do token. Dados desconhecidos não são considerados verificados. MC e FDV são campos independentes, sem substituição.</p></details><h2>Narrativas acompanhadas (podem anteceder o token)</h2>{table(['Tema/link','Origem','Publicado BRT','Registrado BRT','Tokens associados','Confiança'],nr)}<h2>Associações narrativa → token</h2>{table(['Rede','Token','Fonte','Evidência','Temporalidade'],mt)}<h2>Tokens de MC US$ 0–30 mil — amostra disponível</h2>{table(['Rede','Token (DEX Screener)','Detectado BRT','MC','FDV','Liquidez','Compras 5m','Vendas 5m','Idade do pool','X','Site','Narrativas','Risco / dados'],tok)}<h2>Auditoria de cotações usadas pelo simulador</h2>{table(['Operação','Horário BRT','Rede','Etapa','MC','Liquidez','Origem','Elegível','Observação'],attempts)}<h2>Operações fictícias</h2>{table(['Rede','Token','Entrada BRT','MC entrada','Alocação','Status','MC saída','P&L','Motivo'],tr)}<p><small>Meta líquida de US$ 100 é experimental, não garantida. Taxas 0,3% e slippage 2% em cada lado. Stop observado de 10% e limite de 60 minutos. A consulta por minuto não assegura saída ao stop. Um token pode valorizar no painel e ainda assim não ser vendável pelo preço exibido.</small></p></main></body></html>'''
    tmp=PANEL.with_suffix('.tmp');tmp.write_text(htmlpage,encoding='utf-8');tmp.replace(PANEL)

def test():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        c=conn(Path(d)/'test.sqlite');now=time.time()
        c.execute("INSERT INTO narratives VALUES(?,?,?,?,?,?,?,?)",('test-narrative','Moon Cat noticia',json.dumps(['moon cat']),'https://x.com/i/status/123',now-120,now-100,'MANUAL',0))
        p={'chainId':'solana','baseToken':{'address':'TESTTOKEN','symbol':'MoonCat','name':'Moon Cat'},'priceUsd':'0.001','marketCap':10000,'fdv':20000,'pairCreatedAt':(now-60)*1000,'liquidity':{'usd':12000},'txns':{'m5':{'buys':12,'sells':3}},'url':'https://dexscreener.com/solana/TESTPOOL','info':{'socials':[{'platform':'twitter','url':'https://x.com/mooncat'}]}}
        assert tick(c,[p],{},now)==1
        assert c.execute('SELECT count(*) FROM matches').fetchone()[0]==1
        assert c.execute('SELECT mc,fdv FROM tokens').fetchone()['fdv']==20000
        assert c.execute("SELECT count(*) FROM trades WHERE status='OPEN'").fetchone()[0]==1
        p['priceUsd']='0.00085';tick(c,[p],{},now+60)
        assert c.execute("SELECT status FROM trades").fetchone()[0]=='CLOSED'
        assert c.execute("SELECT count(*) FROM execution_quotes WHERE stage='EXIT_ATTEMPT'").fetchone()[0]>=1
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        c.close()
        print('TESTE OK V9.3: narrativas, MC/FDV separados, duas redes no schema, simulacao, SQLite, sem API paga X.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--teste',action='store_true');ap.add_argument('--uma-vez',action='store_true');args=ap.parse_args()
    if args.teste:return test()
    c=conn()
    stop_notifications=threading.Event()
    notifier=threading.Thread(target=notification_worker,args=(DB,stop_notifications),daemon=True)
    notifier.start()
    print('Bot V9.3 | SEM API PAGA DO X | exclusivamente simulacao | Brasilia | Ctrl+C para parar',flush=True)
    last_news=0
    try:
        while True:
            now=time.time();health='Consulta iniciada';errors=[];count=0
            try:
                with c:ingest_watch(c,now)
            except Exception as e:errors.append('narrativas.json: '+str(e)[:140])
            # Sem QUALQUER chamada à API do X, mesmo se houver credencial no ambiente.
            if now-last_news>=NEWS_INTERVAL:
                last_news=now
                try:
                    with c:ingest_free_news(c,now)
                except Exception as e:errors.append('RSS: '+str(e)[:140])
            try:
                pairs,meta,errs,discovered=discover();errors+=errs
                held,held_errors=fetch_open_positions(c);errors+=held_errors
                count=tick(c,pairs,meta,now,held)
                health=f'Candidatos detectados: {discovered}; dentro do MC desejado: {count}'
            except Exception as e:errors.append('mercado: '+repr(e)[:180])
            if errors:
                with c:
                    for e in errors:c.execute('INSERT INTO events(ts,level,message) VALUES(?,?,?)',(now,'WARN',e))
                health += ' | Alertas: '+'; '.join(errors[:3])
            dashboard(c,now,health);print(fmt(now),'|',health,flush=True)
            if args.uma_vez:break
            time.sleep(60)
    except KeyboardInterrupt:print('\nEncerrado. Histórico preservado.')
    finally:
        stop_notifications.set()
        c.close()
if __name__=='__main__': main()
