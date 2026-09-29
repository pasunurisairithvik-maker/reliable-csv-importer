import sqlite3
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.importer import InvalidCSV, MAX_BYTES, connect, import_csv, list_products
from app.main import create_app

HEADER = "product_id,name,price,quantity\n"
class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "inventory.db"
    def tearDown(self): self.tmp.cleanup()
    def load(self, rows): return import_csv((HEADER + rows).encode(), self.db)
    def test_reupload_is_idempotent(self):
        self.assertEqual(self.load("A,Book,2.30,4\n")["accepted"], 1)
        self.assertEqual(self.load("A,Book,2.30,4\n")["skipped"], 1)
        self.assertEqual(list_products(self.db)[0]["price_cents"], 230)
    def test_conflict_does_not_overwrite(self):
        self.load("A,Book,2.30,4\n")
        self.assertEqual(self.load("A,Book,3.00,4\n")["rejected"], 1)
        self.assertEqual(list_products(self.db)[0]["price_cents"], 230)
    def test_invalid_rows_are_explained(self):
        result = self.load("A,Book,NaN,1\nB,Pen,1.001,2\nC,Case,4,-1\nD,,1,2\nE,Good,1.25,3\n")
        self.assertEqual((result["accepted"], result["rejected"]), (1,4))
        self.assertEqual(len(result["issues"]), 4)
    def test_header_and_encoding(self):
        for raw in [b"x,y\n1,2", b"product_id,name,price,price\n", b"\xff"]:
            with self.assertRaises(InvalidCSV): import_csv(raw,self.db)
    def test_size_limit(self):
        with self.assertRaises(InvalidCSV): import_csv(b"x" * (MAX_BYTES+1),self.db)
    def test_malformed_csv_leaves_no_writes(self):
        with self.assertRaises(InvalidCSV): self.load('A,Book,1,2\nB,"unfinished')
        self.assertEqual(list_products(self.db), [])
    def test_database_error_rolls_back(self):
        con=connect(self.db)
        con.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON inventory WHEN NEW.product_id='FAIL' BEGIN SELECT RAISE(ABORT,'test failure'); END")
        con.commit();con.close()
        with self.assertRaises(sqlite3.Error): self.load("A,Book,1,2\nFAIL,Pen,1,2\n")
        self.assertEqual(list_products(self.db), [])
    def test_api_upload_and_validation(self):
        client=TestClient(create_app(self.db))
        response=client.post('/imports',files={'file':('sample.csv',(HEADER+'A,Book,2,3\n').encode(),'text/csv')})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['accepted'],1)
        self.assertEqual(client.get('/products').json()[0]['quantity'],3)
        self.assertEqual(client.get('/products?limit=0').status_code,422)
        self.assertEqual(client.post('/imports',files={'file':('bad.csv',b'bad','text/csv')}).status_code,400)
    def test_api_database_failure(self):
        client=TestClient(create_app(Path(self.tmp.name)))
        response=client.post('/imports',files={'file':('sample.csv',HEADER.encode(),'text/csv')})
        self.assertEqual(response.status_code,503)
    def test_ui(self):
        self.assertIn('Reliable CSV Importer',TestClient(create_app(self.db)).get('/').text)

if __name__ == '__main__': unittest.main()
