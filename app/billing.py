from app.db import db

def create_invoice(engagement_id:int, amount:float, currency:str="SEK", due_date:str|None=None, note:str=""):
    with db() as conn:
        if not conn.execute("SELECT 1 FROM engagements WHERE id=?",(engagement_id,)).fetchone(): raise ValueError("Engagement not found")
        seq=conn.execute("SELECT COALESCE(MAX(id),0)+1 FROM invoices").fetchone()[0]
        number=f"INV-{seq:06d}"
        cur=conn.execute("INSERT INTO invoices(engagement_id,number,currency,amount,due_date,note) VALUES(?,?,?,?,?,?)",(engagement_id,number,currency.upper(),amount,due_date,note))
        return dict(conn.execute("SELECT * FROM invoices WHERE id=?",(cur.lastrowid,)).fetchone())

def list_invoices(engagement_id:int|None=None):
    with db() as conn:
        q="SELECT * FROM invoices"; args=()
        if engagement_id is not None: q+=" WHERE engagement_id=?"; args=(engagement_id,)
        return [dict(r) for r in conn.execute(q+" ORDER BY id DESC",args)]
