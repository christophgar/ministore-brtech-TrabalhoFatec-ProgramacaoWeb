import os
import tempfile
import unittest

temp=tempfile.TemporaryDirectory()
os.environ['STORE_DATABASE']=os.path.join(temp.name,'test.db')
from store import app,db

class StoreTests(unittest.TestCase):
    def setUp(self): self.c=app.test_client(); self.c.get('/')
    def post(self,path,data=None):
        with self.c.session_transaction() as s: token=s['csrf']
        return self.c.post(path,data=dict(data or {},csrf=token),follow_redirects=True)
    def login(self,admin=False):
        return self.post('/login',dict(email='admin@brasiltech.com' if admin else 'ana@email.com',password='Admin@123' if admin else 'Cliente@123'))
    def test_purchase(self):
        self.login(); self.post('/cart/add/1'); self.post('/cart',{'coupon':'BRASIL10'})
        with db() as c: before=c.execute('SELECT stock FROM products WHERE id=1').fetchone()[0]
        r=self.post('/checkout'); self.assertIn('confirmado',r.get_data(as_text=True))
        with db() as c:
            self.assertEqual(c.execute('SELECT total FROM orders ORDER BY id DESC').fetchone()[0],170991)
            self.assertEqual(c.execute('SELECT stock FROM products WHERE id=1').fetchone()[0],before-1)
    def test_permissions_and_csrf(self):
        self.assertEqual(self.c.post('/checkout').status_code,400)
        self.login(); self.assertEqual(self.c.get('/admin').status_code,403)
    def test_admin(self):
        self.login(True)
        self.assertEqual(self.c.get('/admin').status_code,200)
        self.post('/admin',{'action':'coupon','code':'AULA15','percent':'15'})
        self.post('/admin',{'action':'ad','title':'Campanha da aula','body':'Upgrade com desconto'})
        self.assertIn('Campanha da aula',self.c.get('/').get_data(as_text=True))
        self.post('/admin',{'action':'coupon','code':'INVALIDO','percent':'100'})
        with db() as c: self.assertIsNone(c.execute("SELECT * FROM coupons WHERE code='INVALIDO'").fetchone())
    def test_search(self):
        r=self.c.get('/?q=Ryzen').get_data(as_text=True)
        self.assertIn('AMD Ryzen',r); self.assertNotIn('GeForce RTX',r)

if __name__=='__main__': unittest.main()
