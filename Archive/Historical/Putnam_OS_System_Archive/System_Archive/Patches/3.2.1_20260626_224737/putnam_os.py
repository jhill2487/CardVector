import csv, json, os, shutil, sys, webbrowser, statistics, re, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_VERSION='3.1.0'
FLOOR=0.99
REVIEW_THRESHOLD=20.00
EXCLUDE_TERMS=['world championship','worlds',' deck','theme deck','battle deck','starter deck','psa','bgs','cgc','sgc','ace','tag','slab','graded','lot','bundle','playset','4x','x4','pack','booster','wrapper','sealed','proxy','custom','reprint','metal','gold foil','jumbo','oversized']


def user_root():
    env=os.environ.get('USERENVIRONMENT')
    if env: return Path(env)
    return Path.home()/ 'OneDrive' / 'PutnamCollectibles'

ROOT=user_root(); OS_DIR=ROOT/'Putnam_OS'; INCOMING=OS_DIR/'Incoming Files'; COMPLETED=OS_DIR/'Completed Jobs'; LOGS=OS_DIR/'System'/'logs'; CACHE=OS_DIR/'System'/'cache'; SESSIONS=OS_DIR/'Work Sessions'; CONTENT=ROOT/'Putnam_Content'; CONTENT_IDEAS=CONTENT/'Ideas'; CONTENT_RECORDINGS=CONTENT/'Recordings'; CONTENT_CLIPS=CONTENT/'Clips'; CONTENT_EPISODES=CONTENT/'Episodes'
for p in [INCOMING, COMPLETED, LOGS, CACHE, SESSIONS, CONTENT, CONTENT_IDEAS, CONTENT_RECORDINGS, CONTENT_CLIPS, CONTENT_EPISODES]: p.mkdir(parents=True, exist_ok=True)


def nowstamp(): return datetime.now().strftime('%Y%m%d_%H%M%S')
def money(v):
    try: return float(str(v).replace('$','').replace(',','').strip() or 0)
    except: return 0.0

def read_csv(path):
    for enc in ['utf-8-sig','utf-8','cp1252']:
        try:
            with open(path,newline='',encoding=enc) as f: return list(csv.DictReader(f))
        except UnicodeDecodeError: continue
    with open(path,newline='',encoding='utf-8-sig',errors='replace') as f: return list(csv.DictReader(f))

def write_csv(path, rows, fields=None):
    if not fields:
        fields=list(rows[0].keys()) if rows else []
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)



def append_activity(message):
    LOGS.mkdir(parents=True, exist_ok=True)
    line=f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {message}\n"
    with open(LOGS/'activity.log','a',encoding='utf-8') as f:
        f.write(line)

def recent_activity(limit=6):
    path=LOGS/'activity.log'
    if not path.exists(): return []
    try:
        lines=path.read_text(encoding='utf-8-sig').splitlines()
        return lines[-limit:][::-1]
    except Exception:
        return []

def count_files(folder, pattern='*'):
    try: return len([p for p in Path(folder).glob(pattern) if p.is_file()])
    except Exception: return 0

def todays_jobs_count():
    today=datetime.now().strftime('%Y%m%d')
    try: return len([p for p in COMPLETED.iterdir() if p.is_dir() and today in p.name])
    except Exception: return 0

def latest_completed_job():
    try:
        jobs=[p for p in COMPLETED.iterdir() if p.is_dir()]
        if not jobs: return None
        return max(jobs, key=lambda p: p.stat().st_mtime)
    except Exception:
        return None

def create_work_session():
    stamp=nowstamp()
    folder=SESSIONS/f"Work_Session_{stamp}"
    folder.mkdir(parents=True, exist_ok=True)
    note=folder/'session_notes.md'
    note.write_text(f"# Putnam Work Session {stamp}\n\nGoal:\n- \n\nCards planned:\n- \n\nCards completed:\n- \n\nCapture method:\n- Camera / Scanner / Other\n\nContent notes:\n- \n\nBottlenecks observed:\n- \n", encoding='utf-8')
    append_activity(f"Work session started: {folder.name}")
    return folder

def detect_type(rows):
    if not rows: return 'unknown'
    cols=set(rows[0].keys())
    if '*Title' in cols and '*StartPrice' in cols: return 'carduploader_new'
    if any(c.lower()=='itemid' for c in cols) and any('price' in c.lower() for c in cols): return 'active_listings'
    return 'unknown'

def card_fields(row):
    title=row.get('*Title') or row.get('Title') or row.get('title') or ''
    name=row.get('*C:Card Name') or row.get('Card Name') or ''
    setname=row.get('*C:Set') or row.get('Set') or ''
    number=row.get('*C:Card Number') or row.get('Card Number') or ''
    price=money(row.get('*StartPrice') or row.get('StartPrice') or row.get('Price') or row.get('BuyItNowPrice'))
    return title,name,setname,number,price

def build_query(row):
    title,name,setname,number,price=card_fields(row)
    parts=[]
    if name: parts.append(name)
    if setname: parts.append(setname)
    if number: parts.append(number)
    if not parts: parts=[title]
    return ' '.join(parts).strip()

def cache_file(q):
    safe=re.sub(r'[^A-Za-z0-9_.-]+','_',q)[:120]
    return CACHE/(safe+'.json')

def fetch_carduploader_sales(q):
    cf=cache_file(q)
    if cf.exists():
        try:
            data=json.loads(cf.read_text(encoding='utf-8-sig'))
            if data.get('cached_at'): return data
        except Exception: pass
    url='https://carduploader.com/backend/sales/search?q='+urllib.parse.quote(q)
    req=urllib.request.Request(url, headers={'User-Agent':'PutnamOS/3.0 market prototype','Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        data=json.loads(r.read().decode('utf-8'))
    data['cached_at']=datetime.now().isoformat()
    cf.write_text(json.dumps(data,indent=2),encoding='utf-8')
    return data

def comparable_reason(title, name, setname, number):
    t=title.lower()
    for term in EXCLUDE_TERMS:
        if term.strip() in t: return False, f'excluded term: {term.strip()}'
    if name and name.lower() not in t: return False, 'card name not in title'
    if number:
        n=number.lower().replace(' ','')
        t2=t.replace(' ','')
        if n not in t2 and n.lstrip('0') not in t2: return False, 'card number not in title'
    if setname:
        words=[w for w in re.split(r'\W+', setname.lower()) if len(w)>3]
        if words and not any(w in t for w in words): return False, 'set not evident in title'
    return True,'accepted'

def market_analyze(rows):
    reports=[]; rejected=[]
    for i,row in enumerate(rows,1):
        title,name,setname,number,current=card_fields(row); q=build_query(row)
        rec={'row':i,'title':title,'card_name':name,'set':setname,'number':number,'current_price':current,'query':q,'status':'NO_DATA','accepted_count':0,'rejected_count':0,'last_sale':'','last3_avg':'','median':'','reason':''}
        try:
            data=fetch_carduploader_sales(q)
            results=data.get('results',[])
            accepted=[]
            for r in results:
                ok, reason=comparable_reason(r.get('title',''), name, setname, number)
                if ok:
                    accepted.append(r)
                else:
                    rr=dict(rec); rr.update({'candidate_title':r.get('title',''),'candidate_price':r.get('price',''),'reject_reason':reason}); rejected.append(rr)
            prices=[money(r.get('price')) for r in accepted if money(r.get('price'))>0]
            rec['accepted_count']=len(accepted); rec['rejected_count']=max(0,len(results)-len(accepted))
            if prices:
                rec['last_sale']=prices[0]
                rec['last3_avg']=round(sum(prices[:3])/min(3,len(prices)),2)
                rec['median']=round(statistics.median(prices[:min(20,len(prices))]),2)
                if current <= FLOOR and len(prices)>=3 and rec['last3_avg']>=2*FLOOR:
                    rec['status']='MARKET_OPPORTUNITY_REVIEW'
                    rec['reason']=f"Last 3 avg ${rec['last3_avg']:.2f} is >= 2x floor after validation."
                else:
                    rec['status']='NO_CHANGE'
                    rec['reason']='Market data did not exceed opportunity threshold.'
            else:
                rec['reason']='No accepted comparables after validation.'
        except Exception as e:
            rec['status']='ERROR'; rec['reason']=str(e)[:200]
        reports.append(rec)
    return reports,rejected

def audit_new_listing(path, use_market=False):
    rows=read_csv(path); typ=detect_type(rows)
    if typ!='carduploader_new': raise ValueError('This does not appear to be a CardUploader/eBay new-listing CSV.')
    job=COMPLETED/f"Pricing_Analysis_{nowstamp()}"; (job/'source_backup').mkdir(parents=True,exist_ok=True)
    shutil.copy2(path, job/'source_backup'/Path(path).name)
    out_rows=[]; changes=0
    for row in rows:
        r=dict(row); p=money(r.get('*StartPrice'))
        if p < FLOOR:
            r['*StartPrice']=f'{FLOOR:.2f}'; changes+=1
        out_rows.append(r)
    write_csv(job/'ebay_upload_ready.csv', out_rows, list(rows[0].keys()))
    write_csv(job/'review.csv', out_rows, list(rows[0].keys()))
    market_reports=[]; rejected=[]
    if use_market:
        market_reports,rejected=market_analyze(out_rows)
        write_csv(job/'market_report.csv', market_reports)
        if rejected: write_csv(job/'rejected_comps.csv', rejected)
    summary=job/'summary.txt'
    opp=sum(1 for r in market_reports if r.get('status')=='MARKET_OPPORTUNITY_REVIEW')
    summary.write_text(f"Putnam OS v{APP_VERSION}\nRows: {len(rows)}\nFloor changes: {changes}\nMarket opportunities: {opp}\nOutput: {job}\n", encoding='utf-8')
    append_activity(f"Pricing analysis complete: {len(rows)} rows, {opp} market opportunities")
    return job, len(rows), changes, opp

class PutnamOS(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'Putnam OS v{APP_VERSION}')
        self.geometry('1180x760')
        self.configure(bg='#f5f7fb')
        self.loaded=None; self.rows=[]; self.detected=''; self.nav_buttons={}
        self.build_styles(); self.build_ui()
    def build_styles(self):
        s=ttk.Style(self); s.theme_use('clam')
        s.configure('Sidebar.TFrame', background='#101827')
        s.configure('Main.TFrame', background='#f5f7fb')
        s.configure('Card.TFrame', background='white', relief='flat')
        s.configure('Title.TLabel', background='#f5f7fb', foreground='#111827', font=('Segoe UI',22,'bold'))
        s.configure('Sub.TLabel', background='#f5f7fb', foreground='#4b5563', font=('Segoe UI',10))
        s.configure('CardTitle.TLabel', background='white', foreground='#111827', font=('Segoe UI',12,'bold'))
        s.configure('Body.TLabel', background='white', foreground='#374151', font=('Segoe UI',10))
        s.configure('Primary.TButton', font=('Segoe UI',12,'bold'), padding=12)
        s.configure('Secondary.TButton', font=('Segoe UI',10), padding=8)
    def build_ui(self):
        side=ttk.Frame(self, style='Sidebar.TFrame', width=230); side.pack(side='left',fill='y'); side.pack_propagate(False)
        tk.Label(side,text='PUTNAM OS',bg='#101827',fg='white',font=('Segoe UI',22,'bold')).pack(pady=(32,0))
        tk.Label(side,text=f'v{APP_VERSION}',bg='#101827',fg='#9ca3af',font=('Segoe UI',9)).pack(pady=(0,24))
        for name in ['Home','Pricing','Inventory','Shipping','Content','Analytics','Settings']:
            b=tk.Button(side,text=name,anchor='w',bg='#101827',fg='#cbd5e1',activebackground='#243047',activeforeground='white',relief='flat',font=('Segoe UI',11),padx=24,pady=10,command=lambda n=name:self.show_page(n))
            b.pack(fill='x',padx=12,pady=3)
            self.nav_buttons[name]=b
        self.main=ttk.Frame(self, style='Main.TFrame'); self.main.pack(side='left',fill='both',expand=True)
        self.show_page('Home')
    def clear(self):
        for w in self.main.winfo_children(): w.destroy()
    def show_page(self,name):
        for n,b in self.nav_buttons.items():
            b.configure(bg='#182235' if n==name else '#101827', fg='white' if n==name else '#cbd5e1')
        self.clear()
        if name=='Home': self.home_page()
        elif name=='Pricing': self.pricing_page()
        elif name=='Content': self.content_page()
        else:
            ttk.Label(self.main,text=name,style='Title.TLabel').pack(anchor='w',padx=34,pady=(34,6))
            ttk.Label(self.main,text='This workspace is under active development.',style='Sub.TLabel').pack(anchor='w',padx=34)
    def card(self, parent):
        f=tk.Frame(parent,bg='white',highlightbackground='#e5e7eb',highlightthickness=1); return f
    def metric_card(self, parent, title, value, subtitle=''):
        c=self.card(parent); c.pack(side='left',fill='both',expand=True,padx=(0,12),ipady=10)
        tk.Label(c,text=title,bg='white',fg='#6b7280',font=('Segoe UI',9,'bold')).pack(anchor='w',padx=16,pady=(12,2))
        tk.Label(c,text=str(value),bg='white',fg='#111827',font=('Segoe UI',22,'bold')).pack(anchor='w',padx=16)
        if subtitle:
            tk.Label(c,text=subtitle,bg='white',fg='#6b7280',font=('Segoe UI',9)).pack(anchor='w',padx=16,pady=(0,8))
        return c

    def home_page(self):
        ttk.Label(self.main,text='Home',style='Title.TLabel').pack(anchor='w',padx=34,pady=(28,4))
        ttk.Label(self.main,text='Mission control for Putnam Collectibles.',style='Sub.TLabel').pack(anchor='w',padx=34,pady=(0,18))
        wrap=tk.Frame(self.main,bg='#f5f7fb'); wrap.pack(fill='both',expand=True,padx=34,pady=0)
        mission=self.card(wrap); mission.pack(fill='x',pady=(0,16),ipady=12)
        tk.Label(mission,text="Today's Mission",bg='white',fg='#111827',font=('Segoe UI',14,'bold')).pack(anchor='w',padx=18,pady=(14,4))
        last=latest_completed_job()
        mission_text="Analyze the next CardUploader CSV or continue tonight's listing session."
        if last: mission_text=f"Continue the current pipeline. Last completed job: {last.name}"
        tk.Label(mission,text=mission_text,bg='white',fg='#374151',font=('Segoe UI',10),wraplength=820,justify='left').pack(anchor='w',padx=18,pady=(0,12))
        mbtn=tk.Frame(mission,bg='white'); mbtn.pack(anchor='w',padx=18,pady=(0,14))
        ttk.Button(mbtn,text='▶ Analyze & Prepare eBay CSV',style='Primary.TButton',command=lambda:self.show_page('Pricing')).pack(side='left')
        ttk.Button(mbtn,text='Start Work Session',style='Secondary.TButton',command=self.start_work_session).pack(side='left',padx=10)
        ttk.Button(mbtn,text='Open Completed Jobs',style='Secondary.TButton',command=lambda: os.startfile(COMPLETED)).pack(side='left')
        row=tk.Frame(wrap,bg='#f5f7fb'); row.pack(fill='x',pady=(0,16))
        self.metric_card(row,'Pricing Jobs Today',todays_jobs_count(),'Completed job folders')
        self.metric_card(row,'Market Reports',count_files(COMPLETED,'**/market_report.csv'),'Pricing intelligence outputs')
        self.metric_card(row,'Work Sessions',count_files(SESSIONS,'*'),'Tracked sessions')
        self.metric_card(row,'Content Ideas',count_files(CONTENT_IDEAS,'*'),'Backlog items')
        lower=tk.Frame(wrap,bg='#f5f7fb'); lower.pack(fill='both',expand=True)
        activity=self.card(lower); activity.pack(side='left',fill='both',expand=True,padx=(0,12),ipady=10)
        tk.Label(activity,text='Recent Activity',bg='white',fg='#111827',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=18,pady=(12,6))
        acts=recent_activity(7) or ['No activity recorded yet.']
        for a in acts:
            tk.Label(activity,text='✓ '+a,bg='white',fg='#374151',font=('Segoe UI',9),anchor='w',justify='left').pack(anchor='w',padx=18,pady=2)
        content=self.card(lower); content.pack(side='left',fill='both',expand=True,ipady=10)
        tk.Label(content,text='Content Snapshot',bg='white',fg='#111827',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=18,pady=(12,6))
        lines=[
            'Recording status: Not started',
            f"Recordings saved: {count_files(CONTENT_RECORDINGS,'*')}",
            f"Clips captured: {count_files(CONTENT_CLIPS,'*')}",
            f"Episodes planned: {count_files(CONTENT_EPISODES,'*')}",
            'Current concept: Listing workflow / Putnam OS buildout',
        ]
        for line in lines:
            tk.Label(content,text=line,bg='white',fg='#374151',font=('Segoe UI',9),anchor='w').pack(anchor='w',padx=18,pady=2)
        ttk.Button(content,text='Open OBS Recording Checklist',style='Secondary.TButton',command=self.open_recording_checklist).pack(anchor='w',padx=18,pady=12)

    def start_work_session(self):
        folder=create_work_session()
        messagebox.showinfo('Putnam OS',f'Work session folder created:\n{folder}')
        try: os.startfile(folder)
        except Exception: pass
        self.show_page('Home')

    def open_recording_checklist(self):
        checklist=CONTENT/'OBS_Workflow_Recording_Checklist.txt'
        if not checklist.exists():
            checklist.write_text("""Putnam Workflow Recording Checklist

1. Open OBS.
2. Select or create scene: Workflow Analysis.
3. Add Display Capture: Full Desktop.
4. Fit desktop capture to screen.
5. Add Brio camera as picture-in-picture if useful.
6. Confirm lavalier mic meter moves.
7. Recording format: MKV, 1080p, 30 FPS.
8. Start Recording.
9. Work normally. Do not stop for mistakes.
10. Stop recording when session is done.

Goal: Capture the real listing workflow for process improvement and content creation.
""", encoding='utf-8')
        append_activity('Opened OBS recording checklist')
        try: os.startfile(checklist)
        except Exception: messagebox.showinfo('OBS Checklist',str(checklist))

    def content_page(self):
        ttk.Label(self.main,text='Content',style='Title.TLabel').pack(anchor='w',padx=34,pady=(28,4))
        ttk.Label(self.main,text='Track recording sessions, clips, episode ideas, and publishing preparation.',style='Sub.TLabel').pack(anchor='w',padx=34,pady=(0,18))
        wrap=tk.Frame(self.main,bg='#f5f7fb'); wrap.pack(fill='both',expand=True,padx=34,pady=0)
        row=tk.Frame(wrap,bg='#f5f7fb'); row.pack(fill='x',pady=(0,16))
        self.metric_card(row,'Recordings',count_files(CONTENT_RECORDINGS,'*'),'Raw footage')
        self.metric_card(row,'Clips',count_files(CONTENT_CLIPS,'*'),'Potential shorts')
        self.metric_card(row,'Ideas',count_files(CONTENT_IDEAS,'*'),'Backlog')
        self.metric_card(row,'Episodes',count_files(CONTENT_EPISODES,'*'),'Planned videos')
        panel=self.card(wrap); panel.pack(fill='x',ipady=12)
        tk.Label(panel,text='Quick Actions',bg='white',fg='#111827',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=18,pady=(12,8))
        btns=tk.Frame(panel,bg='white'); btns.pack(anchor='w',padx=18,pady=(0,14))
        ttk.Button(btns,text='Open OBS Checklist',style='Secondary.TButton',command=self.open_recording_checklist).pack(side='left')
        ttk.Button(btns,text='Open Content Folder',style='Secondary.TButton',command=lambda: os.startfile(CONTENT)).pack(side='left',padx=10)

    def pricing_page(self):
        ttk.Label(self.main,text='Pricing Workspace',style='Title.TLabel').pack(anchor='w',padx=34,pady=(28,4))
        ttk.Label(self.main,text='Analyze CardUploader and eBay CSVs, validate pricing, and prepare upload-ready files.',style='Sub.TLabel').pack(anchor='w',padx=34,pady=(0,18))
        wrap=tk.Frame(self.main,bg='#f5f7fb'); wrap.pack(fill='both',expand=True,padx=34,pady=0)
        drop=self.card(wrap); drop.pack(fill='x',pady=(0,16),ipady=24)
        tk.Label(drop,text='Drop CSV Here',bg='white',fg='#111827',font=('Segoe UI',18,'bold')).pack(pady=(16,4))
        tk.Label(drop,text='or click Browse to select a CardUploader or eBay CSV',bg='white',fg='#6b7280',font=('Segoe UI',10)).pack()
        ttk.Button(drop,text='Browse for CSV',style='Secondary.TButton',command=self.browse).pack(pady=14)
        info=self.card(wrap); info.pack(fill='x',pady=(0,16),ipady=10)
        self.info_var=tk.StringVar(value='No CSV loaded.')
        tk.Label(info,text='Loaded File',bg='white',fg='#111827',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=18,pady=(12,2))
        tk.Label(info,textvariable=self.info_var,bg='white',fg='#374151',font=('Segoe UI',10),justify='left').pack(anchor='w',padx=18,pady=(0,12))
        flow=self.card(wrap); flow.pack(fill='x',pady=(0,16),ipady=10)
        tk.Label(flow,text='Workflow',bg='white',fg='#111827',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=18,pady=(12,2))
        self.flow_var=tk.StringVar(value='1. Load CSV  →  2. Detect Type  →  3. Analyze Pricing  →  4. Export')
        tk.Label(flow,textvariable=self.flow_var,bg='white',fg='#374151',font=('Segoe UI',10)).pack(anchor='w',padx=18,pady=(0,12))
        actions=tk.Frame(wrap,bg='#f5f7fb'); actions.pack(fill='x',pady=(2,12))
        ttk.Button(actions,text='▶ Analyze & Prepare eBay CSV',style='Primary.TButton',command=self.auto_run).pack(side='left')
        ttk.Button(actions,text='Open Completed Jobs',style='Secondary.TButton',command=lambda: os.startfile(COMPLETED)).pack(side='left',padx=12)
        ttk.Button(actions,text='Open Incoming Files',style='Secondary.TButton',command=lambda: os.startfile(INCOMING)).pack(side='left')
        self.status=tk.StringVar(value='Ready.')
        tk.Label(wrap,textvariable=self.status,bg='#f5f7fb',fg='#374151',font=('Segoe UI',10)).pack(anchor='w',pady=(4,0))
    def browse(self):
        p=filedialog.askopenfilename(filetypes=[('CSV files','*.csv'),('All files','*.*')])
        if not p: return
        self.load(p)
    def load(self,p):
        self.loaded=Path(p); self.rows=read_csv(p); self.detected=detect_type(self.rows)
        self.info_var.set(f'{self.loaded.name}\nDetected: {self.detected}\nRows: {len(self.rows)}')
        self.status.set('CSV loaded. Ready to analyze.')
    def auto_run(self):
        if not self.loaded:
            self.browse();
            if not self.loaded: return
        try:
            if self.detected=='carduploader_new':
                self.status.set('Running price audit and market intelligence...'); self.update()
                job,rows,changes,opp=audit_new_listing(self.loaded, use_market=True)
                self.flow_var.set(f'✓ Loaded {rows} rows  →  ✓ CardUploader export  →  ✓ Market Intelligence complete  →  ✓ Output ready')
                self.status.set(f'Complete. Floor changes: {changes}. Market opportunities: {opp}. Job: {job.name}')
                messagebox.showinfo('Putnam OS',f'Analysis complete.\nRows: {rows}\nFloor changes: {changes}\nMarket opportunities: {opp}\n\nOutput folder:\n{job}')
                os.startfile(job)
            else:
                messagebox.showwarning('Putnam OS','This release currently runs full market intelligence for CardUploader new-listing CSVs. Existing listing revision remains supported in prior pricing flow.')
        except Exception as e:
            self.status.set('Error.'); messagebox.showerror('Putnam OS',str(e))

if __name__=='__main__':
    PutnamOS().mainloop()
