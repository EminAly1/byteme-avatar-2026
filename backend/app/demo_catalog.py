"""Opt-in, bounded DEMO master catalogue. Never creates purchases/lots/sales."""
import argparse
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5
from sqlalchemy import select, text
from app import models as m, schemas as s, services, cuttings
from app.commands import execute
from app.config import get_settings
from app.database import get_engine

PRODUCTS = [
    ('KUZU','Bütün kuzu','raw','kg'), ('ET','Dana eti','raw','kg'),
    ('BAHARAT','Baharat','raw','kg'), ('BAGIRSAK','Bağırsak','raw','kg'),
    ('BUT','Kuzu but','finished','kg'), ('KOL','Kuzu kol','finished','kg'),
    ('SIRT','Kuzu sırt','finished','kg'), ('KABURGA','Kuzu kaburga','finished','kg'),
    ('KIYMA','Kuzu kıyma','finished','kg'), ('SUC','Sucuk paketi','finished','package'),
    ('KEMIK','Kuzu kemik','byproduct','kg'),
]
ALLOWED = {'products','parties','locations','recipe_versions','recipe_lines','idempotency_requests'}


def protected_hash(engine):
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as c:
        c.exec_driver_sql('SET TRANSACTION READ ONLY')
        data = {name:sorted(repr(tuple(row)) for row in c.execute(table.select()))
                for name,table in m.Base.metadata.tables.items() if name not in ALLOWED}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def seed_catalog(confirmation):
    settings = get_settings()
    if (not settings.mysql_database.endswith('_test') or confirmation != settings.mysql_database
            or settings.mysql_host not in {'localhost','127.0.0.1','mysql'}):
        raise SystemExit('Demo yalnız açıkça onaylanan yerel *_test veritabanında çalışır; kayıt değiştirilmedi.')
    engine = get_engine()
    with engine.connect() as c:
        if c.execute(text('SELECT DATABASE()')).scalar_one() != confirmation:
            raise SystemExit('Bağlı veritabanı onayla eşleşmiyor; demo durduruldu.')
    before = protected_hash(engine)
    def write(kind, slug, schema, data, action, model):
        body=schema.model_validate(data)
        result,_=execute(kind,str(uuid5(NAMESPACE_URL,'avatar:demo-catalog:v1:'+kind+':'+slug)),body,action)
        with engine.connect() as c:
            if c.execute(select(model.id).where(model.id==result['id'])).first() is None:
                raise SystemExit('Önceki DEMO kartı silinmiş. Kopya/geri yükleme oluşturulmadı; ayrı yeni test şeması seçin.')
        return result
    products={}
    assert len(PRODUCTS)<=30
    for sku,name,kind,unit in PRODUCTS:
        products[sku]=write('products',sku,s.ProductCreate,{'sku':'DEMO28-'+sku,'name':'DEMO '+name,'type':kind,'base_unit':unit,
            **({'species':'Kuzu'} if sku=='KUZU' else {}),**({'package_weight_kg':'1'} if unit=='package' else {})},services.create_product,m.Product)
    parties={role:write('parties',role,s.PartyCreate,{'name':'DEMO '+name,'roles':[role],'contact':'DEMO · ekip@example.invalid'},services.create_party,m.Party)
        for role,name in [('supplier','Tedarikçi'),('customer','Müşteri'),('producer','Dış üretici')]}
    locations=[write('locations',slug,s.LocationCreate,{'name':'DEMO '+name,'kind':kind,**({'party_id':parties['producer']['id']} if kind=='external_producer' else {})},services.create_location,m.Location)
        for slug,name,kind in [('warehouse','İşletme deposu','warehouse'),('producer','Üretici konumu','external_producer'),('quarantine','Karantina','quarantine')]]
    recipe=write('recipes','lamb',s.RecipeCreate,{'code':'DEMO28-KUZU','version':1,'species':'Kuzu','input_product_id':products['KUZU']['id'],'allocation_method':'quantity',
        'lines':[{'product_id':products[key]['id']} for key in ['BUT','KOL','SIRT','KABURGA','KIYMA']]},cuttings.create_recipe,m.RecipeVersion)
    if protected_hash(engine)!=before:
        raise SystemExit('Katalog dışı tablolar değişti; başka bir işlem çalışmış olabilir. Kayıtlar sıfırlanmadı.')
    return {'data_origin':'DEMO','database':confirmation,'products':list(products.values()),'parties':list(parties.values()),'locations':locations,'recipe':recipe,'financial_tables_unchanged':True}


def main():
    p=argparse.ArgumentParser(description='Demo verilerini hazırla: yalnız katalog, açık test DB onayı zorunlu.')
    p.add_argument('--confirm-database',required=True)
    print(json.dumps(seed_catalog(p.parse_args().confirm_database),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
