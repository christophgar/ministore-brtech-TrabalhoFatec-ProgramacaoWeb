import os, secrets, sqlite3, shutil
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, session, redirect, url_for, flash, abort, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app=Flask(__name__)
app.secret_key=os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
os.makedirs(app.instance_path,exist_ok=True)
DATABASE=os.environ.get('STORE_DATABASE',os.path.join(app.instance_path,'brasiltech.db'))
if not os.path.exists(DATABASE) and 'STORE_DATABASE' not in os.environ:
    shutil.copyfile(Path(__file__).parent/'demo'/'brasiltech.db', DATABASE)
def db():
    c=sqlite3.connect(DATABASE); c.row_factory=sqlite3.Row
    return c
def init():
    with db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,admin INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name TEXT,category TEXT,description TEXT,price INTEGER,stock INTEGER,icon TEXT);
        CREATE TABLE IF NOT EXISTS coupons(code TEXT PRIMARY KEY,percent INTEGER CHECK(percent BETWEEN 1 AND 90));
        CREATE TABLE IF NOT EXISTS ads(id INTEGER PRIMARY KEY,title TEXT,body TEXT,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,user_id INTEGER,total INTEGER,created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY,order_id INTEGER,product_id INTEGER,quantity INTEGER,price INTEGER);''')
        if 'address' not in [r['name'] for r in c.execute('PRAGMA table_info(users)')]:
            c.execute("ALTER TABLE users ADD COLUMN address TEXT DEFAULT ''")
        if not c.execute('SELECT 1 FROM users').fetchone():
            for name,email,password,admin in [('Administrador','admin@brasiltech.com','Admin@123',1),('Ana Silva','ana@email.com','Cliente@123',0),('Pedro Santos','pedro@email.com','Cliente@123',0)]:
                c.execute('INSERT INTO users(name,email,password,admin) VALUES(?,?,?,?)',(name,email,generate_password_hash(password),admin))
        if not c.execute('SELECT 1 FROM products').fetchone():
            c.executemany('INSERT INTO products(name,category,description,price,stock,icon) VALUES(?,?,?,?,?,?)',[
            ('GeForce RTX 4060 8 GB','Placas de vídeo','8 GB GDDR6 • DLSS 3 • Ray tracing',189990,12,'▰'),('AMD Ryzen 7 5700X','Processadores','8 núcleos • 16 threads • AM4',109990,18,'▣'),('Fury Beast 16 GB','Memórias','DDR4 • 3200 MHz • Alto desempenho',24990,30,'▤'),('SSD NVMe 1 TB','Armazenamento','PCIe • Leitura de até 3.500 MB/s',42990,22,'▥'),('Placa-mãe B550M','Placas-mãe','AMD AM4 • DDR4 • Micro ATX',69990,10,'▦'),('Fonte 650 W Bronze','Fontes','80 Plus Bronze • PFC ativo',35990,15,'◉'),('Teclado mecânico RGB','Periféricos','Switch vermelho • ABNT2 • USB',19990,25,'⌨'),('Monitor gamer 24”','Monitores','Full HD • IPS • 165 Hz • 1 ms',89990,8,'▱')])
            c.execute('INSERT INTO coupons(code,percent) VALUES(?,?)',('BRASIL10',10))
            c.execute('INSERT INTO ads(title,body) VALUES(?,?)',('Seu próximo upgrade começa aqui.','Hardware de respeito. Preços que jogam no seu time. Ganhe 10% com o cupom BRASIL10.'))
            c.execute('INSERT INTO orders(user_id,total) VALUES(2,24990)')
            c.execute('INSERT INTO items(order_id,product_id,quantity,price) VALUES(1,3,1,24990)')
            c.execute('UPDATE products SET stock=stock-1 WHERE id=3')
        c.execute("UPDATE users SET address=? WHERE email=? AND COALESCE(address,'')=''",('Rua das Palmeiras, 120 - Centro, São Paulo/SP - CEP 01000-000','ana@email.com'))
        c.execute("UPDATE users SET address=? WHERE email=? AND COALESCE(address,'')=''",('Av. Brasil, 450 - Jardim América, Campinas/SP - CEP 13000-000','pedro@email.com'))
        for column,definition in [('cpf',"TEXT DEFAULT ''")]:
            if column not in [r['name'] for r in c.execute('PRAGMA table_info(users)')]: c.execute(f'ALTER TABLE users ADD COLUMN {column} {definition}')
        for column,definition in [('expires','TEXT'),('category',"TEXT DEFAULT ''"),('once_per_cpf','INTEGER DEFAULT 0')]:
            if column not in [r['name'] for r in c.execute('PRAGMA table_info(coupons)')]: c.execute(f'ALTER TABLE coupons ADD COLUMN {column} {definition}')
        if 'cancelled' not in [r['name'] for r in c.execute('PRAGMA table_info(coupons)')]: c.execute('ALTER TABLE coupons ADD COLUMN cancelled INTEGER DEFAULT 0')
        if 'coupon_code' not in [r['name'] for r in c.execute('PRAGMA table_info(orders)')]: c.execute('ALTER TABLE orders ADD COLUMN coupon_code TEXT')
        if 'expires' not in [r['name'] for r in c.execute('PRAGMA table_info(ads)')]: c.execute('ALTER TABLE ads ADD COLUMN expires TEXT')
        if 'image' not in [r['name'] for r in c.execute('PRAGMA table_info(products)')]: c.execute("ALTER TABLE products ADD COLUMN image TEXT DEFAULT ''")
        c.execute('CREATE TABLE IF NOT EXISTS coupon_uses (code TEXT NOT NULL,cpf TEXT NOT NULL,order_id INTEGER NOT NULL,PRIMARY KEY(code,cpf))')
        c.execute("UPDATE users SET cpf='12345678909' WHERE email='ana@email.com' AND COALESCE(cpf,'')=''")
        c.execute("UPDATE users SET cpf='98765432100' WHERE email='pedro@email.com' AND COALESCE(cpf,'')=''")
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='demo_seed'").fetchone():
            c.execute('CREATE TABLE demo_seed (version INTEGER PRIMARY KEY)')
        if not c.execute('SELECT 1 FROM demo_seed WHERE version=1').fetchone():
            examples=[('ana@email.com',[(1,1),(4,1)]),('pedro@email.com',[(2,1),(3,2)]),('ana@email.com',[(5,1),(6,1)]),('pedro@email.com',[(7,1),(8,1)]),('ana@email.com',[(4,2),(3,1)])]
            for email,lines in examples:
                uid=c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()['id']
                priced=[]
                for pid,qty in lines:
                    p=c.execute('SELECT price,stock FROM products WHERE id=?',(pid,)).fetchone()
                    if not p or p['stock']<qty: raise RuntimeError('Estoque insuficiente para vendas de exemplo')
                    priced.append((pid,qty,p['price']))
                oid=c.execute('INSERT INTO orders(user_id,total) VALUES(?,?)',(uid,sum(qty*price for _,qty,price in priced))).lastrowid
                for pid,qty,price in priced:
                    c.execute('INSERT INTO items(order_id,product_id,quantity,price) VALUES(?,?,?,?)',(oid,pid,qty,price))
                    c.execute('UPDATE products SET stock=stock-? WHERE id=?',(qty,pid))
            c.execute('INSERT INTO demo_seed(version) VALUES(1)')
        if not c.execute('SELECT 1 FROM demo_seed WHERE version=2').fetchone():
            today=date.today()
            for offset in range(11,-1,-1):
                month_index=today.year*12+today.month-1-offset
                year,month=divmod(month_index,12)
                year_month=f'{year:04d}-{month+1:02d}'
                product=c.execute('SELECT id,price FROM products ORDER BY id LIMIT 1 OFFSET ?',(offset%8,)).fetchone()
                customer=c.execute('SELECT id FROM users WHERE email=?',('ana@email.com' if offset%2 else 'pedro@email.com',)).fetchone()
                order_id=c.execute('INSERT INTO orders(user_id,total,created) VALUES(?,?,?)',(customer['id'],product['price'],year_month+'-15 12:00:00')).lastrowid
                c.execute('INSERT INTO items(order_id,product_id,quantity,price) VALUES(?,?,1,?)',(order_id,product['id'],product['price']))
                c.execute('UPDATE products SET stock=stock-1 WHERE id=? AND stock>0',(product['id'],))
            c.execute('INSERT INTO demo_seed(version) VALUES(2)')
init()

@app.template_filter('brl')
def brl(v): return ('R$ {:,.2f}'.format(v/100)).replace(',','X').replace('.',',').replace('X','.')
@app.template_filter('month_br')
def month_br(value):
    months=('Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez')
    year,month=value.split('-')
    return f'{months[int(month)-1]} {year}'
@app.before_request
def csrf():
    session.setdefault('csrf',secrets.token_hex(24))
    if request.method=='POST' and not secrets.compare_digest(session['csrf'],request.form.get('csrf','')): abort(400)
def protected(admin=False):
    def deco(fn):
        @wraps(fn)
        def inner(*args,**kwargs):
            with db() as c: u=c.execute('SELECT * FROM users WHERE id=?',(session.get('uid'),)).fetchone()
            if not u: return redirect(url_for('login'))
            if admin and not u['admin']: abort(403)
            return fn(*args,**kwargs)
        return inner
    return deco
@app.context_processor
def shared():
    with db() as c: u=c.execute('SELECT id,name,admin FROM users WHERE id=?',(session.get('uid'),)).fetchone()
    return dict(user=u,cart_count=sum(session.get('cart',{}).values()))
@app.get('/')
def home():
    q=request.args.get('q',''); category=request.args.get('category','')
    with db() as c:
        products=c.execute("SELECT * FROM products WHERE name LIKE ? AND (?='' OR category=?)",('%'+q+'%',category,category)).fetchall()
        categories=[r[0] for r in c.execute('SELECT DISTINCT category FROM products')]
        ad=c.execute('SELECT * FROM ads WHERE active=1 AND (expires IS NULL OR expires>=?) ORDER BY id DESC LIMIT 1',(date.today().isoformat(),)).fetchone()
    return render_template('store.html',products=products,categories=categories,ad=ad,q=q,category=category)

@app.get('/produto/<int:pid>')
def product_detail(pid):
    with db() as c: product=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
    if not product: abort(404)
    return render_template('product_detail.html',product=product)
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        with db() as c: u=c.execute('SELECT * FROM users WHERE email=?',(request.form.get('email','').strip().lower(),)).fetchone()
        if u and check_password_hash(u['password'],request.form.get('password','')):
            basket=session.get('cart',{}); session.clear(); session.update(uid=u['id'],cart=basket,csrf=secrets.token_hex(24))
            return redirect(url_for('admin' if u['admin'] else 'home'))
        flash('E-mail ou senha incorretos.','error')
    return render_template('login.html')
@app.post('/logout')
def logout():
    session.clear(); return redirect(url_for('home'))
@app.post('/cart/add/<int:pid>')
def add(pid):
    with db() as c: p=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
    if not p: abort(404)
    basket=session.get('cart',{}); key=str(pid)
    if basket.get(key,0)<p['stock']:
        basket[key]=basket.get(key,0)+1; session['cart']=basket; flash('Produto adicionado ao carrinho.','success')
    else: flash('Estoque disponível atingido.','error')
    return redirect(url_for('home'))
def coupon_discount(c,rows):
    code=session.get('coupon','')
    coupon=c.execute('SELECT * FROM coupons WHERE code=?',(code,)).fetchone()
    if not coupon or coupon['cancelled'] or (coupon['expires'] and coupon['expires']<date.today().isoformat()): return 0,None
    if coupon['once_per_cpf']:
        u=c.execute('SELECT cpf FROM users WHERE id=?',(session.get('uid'),)).fetchone()
        if not u or not u['cpf'] or c.execute('SELECT 1 FROM coupon_uses WHERE code=? AND cpf=?',(code,u['cpf'])).fetchone(): return 0,None
    eligible=sum(p['price']*p['quantity'] for p in rows if not coupon['category'] or p['category']==coupon['category'])
    return eligible*coupon['percent']//100, (coupon if eligible else None)
def totals(c):
    rows=[]
    for pid,qty in session.get('cart',{}).items():
        p=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
        if p: rows.append(dict(p,quantity=qty))
    subtotal=sum(p['price']*p['quantity'] for p in rows)
    discount,coupon=coupon_discount(c,rows)
    return rows,subtotal,discount,coupon
@app.route('/cart',methods=['GET','POST'])
def cart():
    if request.method=='POST':
        if 'remove' in request.form:
            basket=session.get('cart',{}); basket.pop(request.form['remove'],None); session['cart']=basket
        else:
            code=request.form.get('coupon','').strip().upper()
            session['coupon']=code
            with db() as c: _,_,_,valid=totals(c)
            if not valid: session.pop('coupon',None)
            flash('Cupom aplicado!' if valid else 'Cupom indisponível para este carrinho ou CPF.','success' if valid else 'error')
        return redirect(url_for('cart'))
    with db() as c: rows,subtotal,discount,_=totals(c)
    return render_template('cart.html',rows=rows,subtotal=subtotal,discount=discount)
@app.post('/checkout')
@protected()
def checkout():
    with db() as c:
        c.execute('BEGIN IMMEDIATE'); rows,subtotal,discount,coupon=totals(c)
        if not rows: return redirect(url_for('cart'))
        if any(p['stock']<p['quantity'] for p in rows):
            flash('Estoque insuficiente. Revise o carrinho.','error'); return redirect(url_for('cart'))
        oid=c.execute('INSERT INTO orders(user_id,total,coupon_code) VALUES(?,?,?)',(session['uid'],subtotal-discount,coupon['code'] if coupon else None)).lastrowid
        if coupon and coupon['once_per_cpf']:
            cpf=c.execute('SELECT cpf FROM users WHERE id=?',(session['uid'],)).fetchone()['cpf']
            c.execute('INSERT INTO coupon_uses(code,cpf,order_id) VALUES(?,?,?)',(coupon['code'],cpf,oid))
        for p in rows:
            c.execute('UPDATE products SET stock=stock-? WHERE id=?',(p['quantity'],p['id']))
            c.execute('INSERT INTO items(order_id,product_id,quantity,price) VALUES(?,?,?,?)',(oid,p['id'],p['quantity'],p['price']))
    session['cart']={}; session.pop('coupon',None); flash(f'Pedido #{oid:04d} confirmado! Demonstração sem cobrança.','success')
    return redirect(url_for('orders'))
@app.get('/orders')
@protected()
def orders():
    with db() as c:
        admin_user=c.execute('SELECT admin FROM users WHERE id=?',(session['uid'],)).fetchone()['admin']
        rows=c.execute('SELECT o.*,u.name FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.id DESC' if admin_user else 'SELECT o.*,u.name FROM orders o JOIN users u ON u.id=o.user_id WHERE o.user_id=? ORDER BY o.id DESC',() if admin_user else (session['uid'],)).fetchall()
    return render_template('orders.html',orders=rows,admin_view=admin_user)
@app.route('/admin',methods=['GET','POST'])
@protected(admin=True)
def admin():
    with db() as c:
        if request.method=='POST':
            try:
                action=request.form.get('action')
                if action=='coupon':
                    code=request.form.get('code','').strip().upper(); percent=int(request.form.get('percent','0'))
                    if not code or len(code)>30 or not 1<=percent<=90: raise ValueError()
                    expires=request.form.get('expires') or None; category=request.form.get('category',''); once=int(request.form.get('once_per_cpf','0'))
                    categories=[r[0] for r in c.execute('SELECT DISTINCT category FROM products')]
                    if category and category not in categories: raise ValueError()
                    if expires:
                        if date.fromisoformat(expires)<date.today(): raise ValueError()
                    if once not in (0,1): raise ValueError()
                    c.execute('INSERT INTO coupons(code,percent,expires,category,once_per_cpf) VALUES(?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET percent=excluded.percent,expires=excluded.expires,category=excluded.category,once_per_cpf=excluded.once_per_cpf,cancelled=0',(code,percent,expires,category,once))
                elif action=='ad':
                    title=request.form.get('title','').strip(); body=request.form.get('body','').strip()
                    expires=request.form.get('expires') or None
                    if not title or not body or len(title)>100 or len(body)>300: raise ValueError()
                    if expires and date.fromisoformat(expires)<date.today(): raise ValueError()
                    c.execute('INSERT INTO ads(title,body,expires) VALUES(?,?,?)',(title,body,expires))
                elif action=='toggle': c.execute('UPDATE ads SET active=1-active WHERE id=?',(int(request.form['id']),))
                flash('Alteração salva.','success')
            except (ValueError,InvalidOperation,sqlite3.IntegrityError): flash('Revise os dados informados.','error')
            return redirect(url_for('admin'))
        sales=c.execute('SELECT o.*,u.name,u.address FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.id DESC').fetchall()
        coupons=c.execute('SELECT * FROM coupons').fetchall(); ads=c.execute('SELECT * FROM ads ORDER BY id DESC').fetchall()
        categories=[r[0] for r in c.execute('SELECT DISTINCT category FROM products')]
        customers=c.execute('SELECT name,email,address,cpf FROM users WHERE admin=0').fetchall()
        items=c.execute('SELECT i.*,p.name FROM items i JOIN products p ON p.id=i.product_id ORDER BY order_id DESC').fetchall()
        inventory=c.execute('SELECT COUNT(*) AS products,COALESCE(SUM(stock),0) AS units FROM products').fetchone()
        months=c.execute("SELECT substr(created,1,7) AS month,COUNT(*) AS count,SUM(total) AS total FROM orders GROUP BY substr(created,1,7) ORDER BY month DESC LIMIT 12").fetchall()
    return render_template('admin.html',sales=sales,revenue=sum(s['total'] for s in sales),coupons=coupons,ads=ads,customers=customers,items=items,categories=categories,today=date.today().isoformat(),inventory=inventory,months=months)

@app.route('/admin/produtos/novo',methods=['GET','POST'])
@protected(admin=True)
def new_product():
    if request.method=='POST':
        try:
            name=request.form.get('name','').strip(); category=request.form.get('category','').strip(); description=request.form.get('description','').strip()
            price=Decimal(request.form.get('price','0').replace(',','.')); stock=int(request.form.get('stock','-1')); cents=int(price*100)
            photo=request.files.get('photo'); image=''
            if not name or not category or len(name)>100 or len(category)>50 or len(description)>500 or price<=0 or price*100!=cents or stock<0: raise ValueError()
            if photo and photo.filename:
                ext=Path(secure_filename(photo.filename)).suffix.lower()
                if ext not in ('.jpg','.jpeg','.png','.webp') or photo.mimetype not in ('image/jpeg','image/png','image/webp'): raise ValueError()
                photo.stream.seek(0,2)
                if photo.stream.tell()>2*1024*1024: raise ValueError()
                photo.stream.seek(0)
                folder=Path(app.static_folder)/'uploads'; folder.mkdir(exist_ok=True)
                image='uploads/'+secrets.token_hex(12)+ext
                photo.save(folder/Path(image).name)
            with db() as c: c.execute('INSERT INTO products(name,category,description,price,stock,icon,image) VALUES(?,?,?,?,?,?,?)',(name,category,description,cents,stock,'▣',image))
            flash('Produto cadastrado.','success'); return redirect(url_for('admin'))
        except (ValueError,InvalidOperation): flash('Revise os dados e a imagem (JPG, PNG ou WebP até 2 MB).','error')
    with db() as c: categories=[r[0] for r in c.execute('SELECT DISTINCT category FROM products')]
    return render_template('new_product.html',categories=categories)

@app.route('/admin/cupons',methods=['GET','POST'])
@protected(admin=True)
def coupon_page():
    if request.method=='POST':
        action=request.form.get('action')
        if action=='cancel':
            with db() as c: c.execute('UPDATE coupons SET cancelled=1 WHERE code=?',(request.form.get('code',''),))
            flash('Cupom cancelado.','success'); return redirect(url_for('coupon_page'))
        return admin()
    with db() as c:
        coupons=c.execute('SELECT * FROM coupons ORDER BY code').fetchall()
        categories=[r[0] for r in c.execute('SELECT DISTINCT category FROM products')]
    return render_template('coupons.html',coupons=coupons,categories=categories)

@app.get('/admin/vendas.xlsx')
@protected(admin=True)
def export_sales():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    with db() as c:
        rows=c.execute('SELECT o.id,o.created,u.name,o.total,o.coupon_code FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.created,o.id').fetchall()
    wb=Workbook(); ws=wb.active; ws.title='Vendas'
    ws.append(['Pedido','Data (UTC)','Mês','Cliente','Total (R$)','Cupom'])
    for row in rows:
        ws.append([row['id'],row['created'],row['created'][:7],row['name'],row['total']/100,row['coupon_code'] or ''])
    for cell in ws[1]: cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='146B49')
    for cell in ws['E'][1:]: cell.number_format='"R$" #,##0.00'
    for column,width in {'A':12,'B':22,'C':12,'D':28,'E':18,'F':18}.items(): ws.column_dimensions[column].width=width
    ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
    output=BytesIO(); wb.save(output); output.seek(0)
    return send_file(output,as_attachment=True,download_name='brasiltech-vendas.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.get('/admin/etiqueta/<int:order_id>')
@protected(admin=True)
def shipping_label(order_id):
    with db() as c:
        order=c.execute('SELECT o.*,u.name,u.address FROM orders o JOIN users u ON u.id=o.user_id WHERE o.id=?',(order_id,)).fetchone()
        if not order: abort(404)
        items=c.execute('SELECT p.name,i.quantity FROM items i JOIN products p ON p.id=i.product_id WHERE i.order_id=?',(order_id,)).fetchall()
    return render_template('shipping_label.html',order=order,items=items)

@app.get('/admin/pedido/<int:order_id>')
@protected(admin=True)
def order_detail(order_id):
    with db() as c:
        order=c.execute('SELECT o.*,u.name,u.email,u.address,u.cpf FROM orders o JOIN users u ON u.id=o.user_id WHERE o.id=?',(order_id,)).fetchone()
        if not order: abort(404)
        items=c.execute('SELECT p.name,i.quantity,i.price FROM items i JOIN products p ON p.id=i.product_id WHERE i.order_id=?',(order_id,)).fetchall()
    return render_template('order_detail.html',order=order,items=items)

@app.get('/pedido/<int:order_id>')
@protected()
def customer_order_detail(order_id):
    with db() as c:
        order=c.execute('SELECT * FROM orders WHERE id=? AND user_id=?',(order_id,session['uid'])).fetchone()
        if not order: abort(404)
        items=c.execute('SELECT p.name,i.quantity,i.price FROM items i JOIN products p ON p.id=i.product_id WHERE i.order_id=?',(order_id,)).fetchall()
    return render_template('customer_order.html',order=order,items=items)
