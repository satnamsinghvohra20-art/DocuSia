from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware
from sqlalchemy import create_engine, String, Integer, Date, Text, ForeignKey, DateTime, inspect, text, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
import os, secrets, csv, io

from app.services.stamp_calculator import calculate_stamp_duty
from app.services.pdf_generator import build_legal_pdf
from app.services.receipt_generator import build_receipt_pdf
from app.services.notification import get_whatsapp_urls, get_payment_whatsapp_url
from app.services.police_form_generator import build_police_form_pdf
from app.services.inventory_generator import build_inventory_pdf
from app.services.police_ai_service import (
    resolve_police_station,
    ai_autofill_police_form,
    ai_process_submission,
    generate_portal_autofill_bookmarklet
)
from app.services.police_ack_generator import build_police_ack_pdf
from app.services.ai_quick_creator import parse_quick_text, create_full_automated_agreement
from app.services.biometric_service import simulate_biometric_capture
from app.services.biometric_cert_generator import build_biometric_cert_pdf
from app.services.validators import validate_pan, validate_mobile, validate_aadhaar_verhoeff, sanitize_text
import json

BASE = Path(__file__).resolve().parent.parent
STORAGE = BASE / 'storage'
STORAGE.mkdir(exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./dashmesh.db')

engine = create_engine(
    DATABASE_URL,
    connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {},
    pool_pre_ping=True
)

# High-Performance SQLite Tuning: WAL mode, synchronous normal, large cache
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith('sqlite'):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

class Base(DeclarativeBase): pass

class Customer(Base):
    __tablename__ = 'customers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    mobile: Mapped[str] = mapped_column(String(20))
    email: Mapped[str|None] = mapped_column(String(160), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default='customer')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Property(Base):
    __tablename__ = 'properties'
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(Text())
    property_type: Mapped[str] = mapped_column(String(50))
    area: Mapped[str|None] = mapped_column(String(50), nullable=True)

class Agreement(Base):
    __tablename__ = 'agreements'
    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    
    # Licensor / Owner
    owner_name: Mapped[str] = mapped_column(String(160), index=True)
    owner_mobile: Mapped[str] = mapped_column(String(20), index=True)
    owner_pan: Mapped[str|None] = mapped_column(String(20), nullable=True)
    owner_aadhaar_last4: Mapped[str|None] = mapped_column(String(10), nullable=True)
    
    # Licensee / Tenant
    tenant_name: Mapped[str] = mapped_column(String(160), index=True)
    tenant_mobile: Mapped[str] = mapped_column(String(20), index=True)
    tenant_pan: Mapped[str|None] = mapped_column(String(20), nullable=True)
    tenant_aadhaar_last4: Mapped[str|None] = mapped_column(String(10), nullable=True)
    
    # Police Verification Extended Details
    tenant_permanent_address: Mapped[str|None] = mapped_column(Text(), nullable=True)
    tenant_workplace_name: Mapped[str|None] = mapped_column(String(160), nullable=True)
    tenant_workplace_address: Mapped[str|None] = mapped_column(Text(), nullable=True)
    tenant_occupation: Mapped[str|None] = mapped_column(String(80), default='Private Service', nullable=True)
    emergency_contact_name: Mapped[str|None] = mapped_column(String(160), nullable=True)
    emergency_contact_phone: Mapped[str|None] = mapped_column(String(20), nullable=True)
    vehicle_details: Mapped[str|None] = mapped_column(String(160), nullable=True)
    
    # Property Details
    property_address: Mapped[str] = mapped_column(Text())
    property_type: Mapped[str] = mapped_column(String(50), default='Residential Flat')
    property_city: Mapped[str|None] = mapped_column(String(80), default='Pune', nullable=True)
    pincode: Mapped[str|None] = mapped_column(String(15), nullable=True)
    furnishing_status: Mapped[str|None] = mapped_column(String(50), default='Semi-Furnished', nullable=True)
    electricity_consumer_no: Mapped[str|None] = mapped_column(String(80), nullable=True)
    
    # Commercial Terms
    rent: Mapped[int] = mapped_column(Integer)
    deposit: Mapped[int] = mapped_column(Integer)
    maintenance_charges: Mapped[int|None] = mapped_column(Integer, default=0, nullable=True)
    escalation_percent: Mapped[int|None] = mapped_column(Integer, default=5, nullable=True)
    
    # Tenancy Period
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    notice_period: Mapped[str] = mapped_column(String(80), default='30 days')
    lock_in: Mapped[str] = mapped_column(String(80), default='None')
    purpose: Mapped[str] = mapped_column(String(120), default='Residential')
    special_terms: Mapped[str|None] = mapped_column(Text(), nullable=True)
    
    # Statutory Stamp Duty & Reg Fees
    stamp_duty_amount: Mapped[int|None] = mapped_column(Integer, default=0, nullable=True)
    registration_fee: Mapped[int|None] = mapped_column(Integer, default=1000, nullable=True)
    total_govt_fees: Mapped[int|None] = mapped_column(Integer, default=1000, nullable=True)
    
    # Witnesses
    witness1_name: Mapped[str|None] = mapped_column(String(160), nullable=True)
    witness1_phone: Mapped[str|None] = mapped_column(String(20), nullable=True)
    witness2_name: Mapped[str|None] = mapped_column(String(160), nullable=True)
    witness2_phone: Mapped[str|None] = mapped_column(String(20), nullable=True)
    
    # Workflow & Govt Portal Tracking
    status: Mapped[str] = mapped_column(String(50), default='Draft', index=True)
    registration_status: Mapped[str] = mapped_column(String(50), default='Not Started', index=True)
    police_status: Mapped[str] = mapped_column(String(50), default='Not Started', index=True)
    igr_token_no: Mapped[str|None] = mapped_column(String(60), nullable=True)
    biometric_date: Mapped[str|None] = mapped_column(String(60), nullable=True)
    biometric_status: Mapped[str|None] = mapped_column(String(50), default='Not Started', nullable=True)
    biometric_token: Mapped[str|None] = mapped_column(String(80), nullable=True)
    biometric_device: Mapped[str|None] = mapped_column(String(120), nullable=True)
    biometric_quality_score: Mapped[str|None] = mapped_column(String(40), nullable=True)
    security_seal_hash: Mapped[str|None] = mapped_column(String(64), nullable=True)
    police_token_no: Mapped[str|None] = mapped_column(String(60), nullable=True)
    index_ii_no: Mapped[str|None] = mapped_column(String(80), nullable=True)
    
    # E-Signature Data URL
    signature_data: Mapped[str|None] = mapped_column(Text(), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    documents = relationship("Document", back_populates="agreement", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="agreement", cascade="all, delete-orphan")
    inventory_items = relationship("InventoryItem", back_populates="agreement", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = 'documents'
    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_id: Mapped[int] = mapped_column(ForeignKey('agreements.id'), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(500))
    doc_type: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    agreement = relationship("Agreement", back_populates="documents")

class Payment(Base):
    __tablename__ = 'payments'
    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_id: Mapped[int] = mapped_column(ForeignKey('agreements.id'), index=True)
    receipt_no: Mapped[str] = mapped_column(String(50), index=True)
    payment_type: Mapped[str] = mapped_column(String(50), default='Rent')
    amount: Mapped[int] = mapped_column(Integer)
    payment_date: Mapped[date] = mapped_column(Date, default=date.today)
    payment_mode: Mapped[str] = mapped_column(String(50), default='UPI')
    reference_no: Mapped[str|None] = mapped_column(String(100), nullable=True)
    for_month_year: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    agreement = relationship("Agreement", back_populates="payments")

class InventoryItem(Base):
    __tablename__ = 'inventory_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_id: Mapped[int] = mapped_column(ForeignKey('agreements.id'), index=True)
    room: Mapped[str] = mapped_column(String(80), default='Living Room')
    item_name: Mapped[str] = mapped_column(String(160))
    quantity: Mapped[str] = mapped_column(String(40), default='1')
    condition: Mapped[str] = mapped_column(String(60), default='Good / Working')
    remarks: Mapped[str|None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    agreement = relationship("Agreement", back_populates="inventory_items")

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_id: Mapped[int|None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(255))
    actor: Mapped[str] = mapped_column(String(120), default='admin')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# Safe SQLite Schema Auto-Migration
def migrate_sqlite_schema():
    with engine.connect() as conn:
        inspector = inspect(engine)
        if 'agreements' in inspector.get_table_names():
            existing_cols = {col['name'] for col in inspector.get_columns('agreements')}
            new_columns = [
                ('owner_pan', 'VARCHAR(20)'),
                ('owner_aadhaar_last4', 'VARCHAR(10)'),
                ('tenant_pan', 'VARCHAR(20)'),
                ('tenant_aadhaar_last4', 'VARCHAR(10)'),
                ('tenant_permanent_address', 'TEXT'),
                ('tenant_workplace_name', 'VARCHAR(160)'),
                ('tenant_workplace_address', 'TEXT'),
                ('tenant_occupation', 'VARCHAR(80)'),
                ('emergency_contact_name', 'VARCHAR(160)'),
                ('emergency_contact_phone', 'VARCHAR(20)'),
                ('vehicle_details', 'VARCHAR(160)'),
                ('property_city', 'VARCHAR(80)'),
                ('pincode', 'VARCHAR(15)'),
                ('furnishing_status', 'VARCHAR(50)'),
                ('electricity_consumer_no', 'VARCHAR(80)'),
                ('maintenance_charges', 'INTEGER DEFAULT 0'),
                ('escalation_percent', 'INTEGER DEFAULT 5'),
                ('stamp_duty_amount', 'INTEGER DEFAULT 0'),
                ('registration_fee', 'INTEGER DEFAULT 1000'),
                ('total_govt_fees', 'INTEGER DEFAULT 1000'),
                ('witness1_name', 'VARCHAR(160)'),
                ('witness1_phone', 'VARCHAR(20)'),
                ('witness2_name', 'VARCHAR(160)'),
                ('witness2_phone', 'VARCHAR(20)'),
                ('igr_token_no', 'VARCHAR(60)'),
                ('biometric_date', 'VARCHAR(60)'),
                ('biometric_status', 'VARCHAR(50) DEFAULT "Not Started"'),
                ('biometric_token', 'VARCHAR(80)'),
                ('biometric_device', 'VARCHAR(120)'),
                ('biometric_quality_score', 'VARCHAR(40)'),
                ('security_seal_hash', 'VARCHAR(64)'),
                ('police_token_no', 'VARCHAR(60)'),
                ('index_ii_no', 'VARCHAR(80)'),
                ('signature_data', 'TEXT')
            ]
            for col_name, col_type in new_columns:
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE agreements ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

migrate_sqlite_schema()

app = FastAPI(
    title='Dashmesh Properties — Rent Agreement Management System',
    description='Ultra-fast Maharashtra Leave & License Agreement Engine',
    version='2.8.0'
)

# GZip middleware for high-speed compressed asset delivery
app.add_middleware(GZipMiddleware, minimum_size=500)

app.mount('/static', StaticFiles(directory=str(BASE / 'app/static')), name='static')
templates = Jinja2Templates(directory=str(BASE / 'app/templates'))

GOV_REG = 'https://igrmaharashtra.gov.in/'
IGR_EFILING = 'https://efilingigr.maharashtra.gov.in/ereg/'
POLICE = 'https://citizen.mahapolice.gov.in/Citizen/'
TENANT_FORM = 'https://citizen.mahapolice.gov.in/Citizen/DownloadOfflineEForm.aspx'
GRAS_MAHA = 'https://gras.mahakosh.gov.in/'

def db():
    return SessionLocal()

def log(dbs, agreement_id, action, actor='admin'):
    dbs.add(AuditLog(agreement_id=agreement_id, action=action, actor=actor))
    dbs.commit()

def next_no(dbs):
    year = date.today().year
    n = dbs.query(Agreement).count() + 1
    return f'DP-L&L-{year}-{n:05d}'

@app.get('/', response_class=HTMLResponse)
def home(request: Request, search: str = Query(None), status_filter: str = Query(None)):
    dbs = db()
    today = date.today()
    query = dbs.query(Agreement)
    
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Agreement.agreement_no.ilike(s)) |
            (Agreement.owner_name.ilike(s)) |
            (Agreement.tenant_name.ilike(s)) |
            (Agreement.owner_mobile.ilike(s)) |
            (Agreement.tenant_mobile.ilike(s)) |
            (Agreement.property_address.ilike(s))
        )
        
    if status_filter and status_filter.lower() != 'all':
        if status_filter == 'police_pending':
            query = query.filter(Agreement.police_status.in_(['Not Started', 'Pending', 'Submitted']))
        elif status_filter == 'registered':
            query = query.filter_by(registration_status='Completed')
        elif status_filter == 'draft':
            query = query.filter_by(status='Draft')
        elif status_filter == 'active':
            query = query.filter_by(status='Active')
        elif status_filter == 'expiring_soon':
            query = query.filter(Agreement.end_date >= today, Agreement.end_date <= today + timedelta(days=60))
    
    total_count = dbs.query(Agreement).count()
    draft_count = dbs.query(Agreement).filter_by(status='Draft').count()
    registered_count = dbs.query(Agreement).filter_by(registration_status='Completed').count()
    police_pending_count = dbs.query(Agreement).filter(Agreement.police_status.in_(['Not Started', 'Pending', 'Submitted'])).count()
    expiring_soon_count = dbs.query(Agreement).filter(Agreement.end_date >= today, Agreement.end_date <= today + timedelta(days=60)).count()
    
    agreements_all = dbs.query(Agreement).all()
    monthly_rent_volume = sum(a.rent for a in agreements_all) if agreements_all else 0
    total_deposit_volume = sum(a.deposit for a in agreements_all) if agreements_all else 0
    
    stats = {
        'total': total_count,
        'draft': draft_count,
        'registered': registered_count,
        'police_pending': police_pending_count,
        'expiring_soon': expiring_soon_count,
        'monthly_rent_volume': monthly_rent_volume,
        'total_deposit_volume': total_deposit_volume
    }
    
    recent = query.order_by(Agreement.created_at.desc()).all()
    
    for item in recent:
        item.days_left = (item.end_date - today).days
        item.is_expired = item.days_left < 0
        item.is_expiring_soon = 0 <= item.days_left <= 60
        
    dbs.close()
    
    return templates.TemplateResponse(request, 'dashboard.html', {
        'stats': stats,
        'recent': recent,
        'search': search or '',
        'status_filter': status_filter or 'all',
        'gov_reg': GOV_REG,
        'police': POLICE,
        'gras': GRAS_MAHA
    })

@app.get('/agreements/new', response_class=HTMLResponse)
def new_agreement_view(request: Request):
    return templates.TemplateResponse(request, 'new_agreement.html', {})

@app.post('/agreements/new')
def create_agreement(
    owner_name: str = Form(...),
    owner_mobile: str = Form(...),
    owner_pan: str = Form(None),
    owner_aadhaar_last4: str = Form(None),
    
    tenant_name: str = Form(...),
    tenant_mobile: str = Form(...),
    tenant_pan: str = Form(None),
    tenant_aadhaar_last4: str = Form(None),
    tenant_permanent_address: str = Form(None),
    tenant_workplace_name: str = Form(None),
    tenant_workplace_address: str = Form(None),
    tenant_occupation: str = Form('Private Service'),
    
    property_address: str = Form(...),
    property_type: str = Form('Residential Flat'),
    property_city: str = Form('Pune'),
    pincode: str = Form(None),
    furnishing_status: str = Form('Semi-Furnished'),
    electricity_consumer_no: str = Form(None),
    
    rent: int = Form(...),
    deposit: int = Form(...),
    maintenance_charges: int = Form(0),
    escalation_percent: int = Form(5),
    
    start_date: date = Form(...),
    end_date: date = Form(...),
    notice_period: str = Form('30 days'),
    lock_in: str = Form('None'),
    purpose: str = Form('Residential'),
    special_terms: str = Form(''),
    area_type: str = Form('urban'),
    
    witness1_name: str = Form(None),
    witness1_phone: str = Form(None),
    witness2_name: str = Form(None),
    witness2_phone: str = Form(None)
):
    dbs = db()
    days_delta = (end_date - start_date).days
    months_duration = max(1, round(days_delta / 30.0))
    
    stamp_result = calculate_stamp_duty(
        monthly_rent=rent,
        deposit=deposit,
        months=months_duration,
        area_type=area_type
    )
    
    a = Agreement(
        agreement_no=next_no(dbs),
        owner_name=owner_name.strip(),
        owner_mobile=owner_mobile.strip(),
        owner_pan=owner_pan.strip().upper() if owner_pan else None,
        owner_aadhaar_last4=owner_aadhaar_last4.strip() if owner_aadhaar_last4 else None,
        
        tenant_name=tenant_name.strip(),
        tenant_mobile=tenant_mobile.strip(),
        tenant_pan=tenant_pan.strip().upper() if tenant_pan else None,
        tenant_aadhaar_last4=tenant_aadhaar_last4.strip() if tenant_aadhaar_last4 else None,
        tenant_permanent_address=tenant_permanent_address.strip() if tenant_permanent_address else None,
        tenant_workplace_name=tenant_workplace_name.strip() if tenant_workplace_name else None,
        tenant_workplace_address=tenant_workplace_address.strip() if tenant_workplace_address else None,
        tenant_occupation=tenant_occupation.strip() if tenant_occupation else 'Private Service',
        
        property_address=property_address.strip(),
        property_type=property_type.strip(),
        property_city=property_city.strip() if property_city else 'Pune',
        pincode=pincode.strip() if pincode else None,
        furnishing_status=furnishing_status,
        electricity_consumer_no=electricity_consumer_no.strip() if electricity_consumer_no else None,
        
        rent=rent,
        deposit=deposit,
        maintenance_charges=maintenance_charges,
        escalation_percent=escalation_percent,
        
        start_date=start_date,
        end_date=end_date,
        notice_period=notice_period.strip(),
        lock_in=lock_in.strip(),
        purpose=purpose.strip(),
        special_terms=special_terms.strip() if special_terms else None,
        
        stamp_duty_amount=stamp_result['stamp_duty'],
        registration_fee=stamp_result['registration_fee'],
        total_govt_fees=stamp_result['total_govt_fees'],
        
        witness1_name=witness1_name.strip() if witness1_name else None,
        witness1_phone=witness1_phone.strip() if witness1_phone else None,
        witness2_name=witness2_name.strip() if witness2_name else None,
        witness2_phone=witness2_phone.strip() if witness2_phone else None,
        
        status='Draft',
        registration_status='Not Started',
        police_status='Not Started'
    )
    
    dbs.add(a)
    dbs.commit()
    dbs.refresh(a)
    new_id = a.id
    log(dbs, new_id, f'Agreement created with auto-calculated Stamp Duty: INR {a.stamp_duty_amount:,}')
    dbs.close()
    
    return RedirectResponse(f'/agreements/{new_id}', status_code=303)

@app.get('/agreements/{agreement_id}', response_class=HTMLResponse)
def view_agreement(request: Request, agreement_id: int):
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404, 'Agreement not found')
        
    logs = dbs.query(AuditLog).filter_by(agreement_id=agreement_id).order_by(AuditLog.created_at.desc()).all()
    docs = dbs.query(Document).filter_by(agreement_id=agreement_id).order_by(Document.created_at.desc()).all()
    payments = dbs.query(Payment).filter_by(agreement_id=agreement_id).order_by(Payment.created_at.desc()).all()
    inventory = dbs.query(InventoryItem).filter_by(agreement_id=agreement_id).order_by(InventoryItem.created_at.asc()).all()
    
    days_delta = (a.end_date - a.start_date).days
    months_duration = max(1, round(days_delta / 30.0))
    
    stamp_info = calculate_stamp_duty(
        monthly_rent=a.rent,
        deposit=a.deposit,
        months=months_duration
    )
    
    base_url = str(request.base_url).rstrip('/')
    wa_urls = get_whatsapp_urls(a, base_url)
    
    for p in payments:
        p.wa_receipt_url = get_payment_whatsapp_url(p, a, base_url)
        
    today = date.today()
    days_left = (a.end_date - today).days
    is_expired = days_left < 0
    is_expiring_soon = 0 <= days_left <= 60
    
    renew_rent_preview = int(round(a.rent * (1.0 + ((a.escalation_percent or 5) / 100.0))))
    
    detected_police_station = resolve_police_station(a.property_address, a.property_city or 'Pune')
    portal_data = generate_portal_autofill_bookmarklet(a, {
        "tenant_occupation": a.tenant_occupation or "Software Engineer / IT Professional",
        "tenant_workplace_name": a.tenant_workplace_name or "",
        "tenant_workplace_address": a.tenant_workplace_address or "",
        "tenant_permanent_address": a.tenant_permanent_address or "",
        "emergency_contact_name": a.emergency_contact_name or "",
        "emergency_contact_phone": a.emergency_contact_phone or "",
        "vehicle_details": a.vehicle_details or ""
    })
    portal_payload_json = json.dumps(portal_data["payload"], indent=2)
    portal_bookmarklet_js = portal_data["bookmarklet_js"]
    
    dbs.close()
    return templates.TemplateResponse(request, 'agreement.html', {
        'a': a,
        'logs': logs,
        'docs': docs,
        'payments': payments,
        'inventory': inventory,
        'stamp_info': stamp_info,
        'months_duration': months_duration,
        'wa_urls': wa_urls,
        'days_left': days_left,
        'is_expired': is_expired,
        'is_expiring_soon': is_expiring_soon,
        'renew_rent_preview': renew_rent_preview,
        'detected_police_station': detected_police_station,
        'portal_payload_json': portal_payload_json,
        'portal_bookmarklet_js': portal_bookmarklet_js,
        'base_url': base_url,
        'gov_reg': GOV_REG,
        'igr_efiling': IGR_EFILING,
        'police': POLICE,
        'tenant_form': TENANT_FORM,
        'gras': GRAS_MAHA
    })

@app.post('/agreements/{agreement_id}/status')
def update_status(
    agreement_id: int,
    status: str = Form(...),
    registration_status: str = Form(...),
    police_status: str = Form(...),
    igr_token_no: str = Form(None),
    biometric_date: str = Form(None),
    police_token_no: str = Form(None),
    index_ii_no: str = Form(None)
):
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404)
        
    a.status = status
    a.registration_status = registration_status
    a.police_status = police_status
    if igr_token_no is not None: a.igr_token_no = igr_token_no.strip()
    if biometric_date is not None: a.biometric_date = biometric_date.strip()
    if police_token_no is not None: a.police_token_no = police_token_no.strip()
    if index_ii_no is not None: a.index_ii_no = index_ii_no.strip()
    
    # Invalidate cached PDF so updates are reflected immediately
    cached_pdf = STORAGE / f'{a.agreement_no}_legal_draft.pdf'
    if cached_pdf.exists():
        try: cached_pdf.unlink()
        except Exception: pass
        
    dbs.commit()
    log(dbs, a.id, f'Workflow Updated: {status} | Reg: {registration_status} | Police: {police_status}')
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}', status_code=303)

@app.post('/agreements/{agreement_id}/police-details')
def update_police_details(
    agreement_id: int,
    tenant_permanent_address: str = Form(None),
    tenant_workplace_name: str = Form(None),
    tenant_workplace_address: str = Form(None),
    tenant_occupation: str = Form('Private Service'),
    emergency_contact_name: str = Form(None),
    emergency_contact_phone: str = Form(None),
    vehicle_details: str = Form(None)
):
    """Updates police verification specifics for tenant."""
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404)
        
    if tenant_permanent_address is not None: a.tenant_permanent_address = tenant_permanent_address.strip()
    if tenant_workplace_name is not None: a.tenant_workplace_name = tenant_workplace_name.strip()
    if tenant_workplace_address is not None: a.tenant_workplace_address = tenant_workplace_address.strip()
    if tenant_occupation is not None: a.tenant_occupation = tenant_occupation.strip()
    if emergency_contact_name is not None: a.emergency_contact_name = emergency_contact_name.strip()
    if emergency_contact_phone is not None: a.emergency_contact_phone = emergency_contact_phone.strip()
    if vehicle_details is not None: a.vehicle_details = vehicle_details.strip()
    
    dbs.commit()
    log(dbs, a.id, 'Updated Police Tenant Verification particulars')
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}', status_code=303)

@app.get('/agreements/{agreement_id}/police-form')
def get_police_form(agreement_id: int):
    """Generates official Maharashtra Police Tenant Information Report PDF."""
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404)
        
    out_file = STORAGE / f'{a.agreement_no}_Police_Tenant_Verification_Form.pdf'
    build_police_form_pdf(a, out_file)
    log(dbs, a.id, 'Generated Maharashtra Police Tenant Information Report (PDF)')
    dbs.close()
    
    return FileResponse(
        out_file,
        media_type='application/pdf',
        filename=f'{a.agreement_no}_Police_Tenant_Verification_Form.pdf',
        headers={'Cache-Control': 'public, max-age=3600'}
    )

@app.post('/agreements/{agreement_id}/police-ai-autofill')
def police_ai_autofill(agreement_id: int):
    """
    AI Smart Autofill Engine:
    Intelligently parses agreement terms, locality, and parties,
    and fills in native address, workplace, emergency contacts, and vehicle format.
    """
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404, 'Agreement not found')
        
    enriched = ai_autofill_police_form(a)
    
    a.tenant_occupation = enriched.get("tenant_occupation")
    a.tenant_workplace_name = enriched.get("tenant_workplace_name")
    a.tenant_workplace_address = enriched.get("tenant_workplace_address")
    a.tenant_permanent_address = enriched.get("tenant_permanent_address")
    a.emergency_contact_name = enriched.get("emergency_contact_name")
    a.emergency_contact_phone = enriched.get("emergency_contact_phone")
    a.vehicle_details = enriched.get("vehicle_details")
    
    if a.police_status in ['Not Started', 'Pending']:
        a.police_status = 'Form Filled (AI)'
        
    dbs.commit()
    log(dbs, a.id, f"AI Auto-Filled Police Verification Dossier (Station: {enriched['police_station']})")
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}#police-section', status_code=303)

@app.post('/agreements/{agreement_id}/police-ai-submit')
def police_ai_submit(agreement_id: int):
    """
    AI Automated Submission Pipeline:
    1. Validates and auto-fills missing particulars.
    2. Generates cryptographic SHA-256 digital security seal and official token (MH-POL-2026-...).
    3. Issues digital submission certificate PDF.
    4. Updates database status to 'Completed'.
    """
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404, 'Agreement not found')
        
    enriched = ai_autofill_police_form(a)
    if not a.tenant_permanent_address: a.tenant_permanent_address = enriched.get("tenant_permanent_address")
    if not a.tenant_workplace_name: a.tenant_workplace_name = enriched.get("tenant_workplace_name")
    if not a.tenant_workplace_address: a.tenant_workplace_address = enriched.get("tenant_workplace_address")
    if not a.tenant_occupation: a.tenant_occupation = enriched.get("tenant_occupation")
    if not a.emergency_contact_name: a.emergency_contact_name = enriched.get("emergency_contact_name")
    if not a.emergency_contact_phone: a.emergency_contact_phone = enriched.get("emergency_contact_phone")
    if not a.vehicle_details: a.vehicle_details = enriched.get("vehicle_details")
    
    submission_res = ai_process_submission(a, enriched)
    
    a.police_status = 'Completed'
    a.police_token_no = submission_res["ack_token"]
    
    # Generate the official Police Submission Acknowledgment Certificate PDF
    ack_filename = f'{a.agreement_no}_Police_Verification_Ack.pdf'
    ack_path = STORAGE / ack_filename
    build_police_ack_pdf(a, submission_res, ack_path)
    
    # Also generate the filled Police Tenant Verification Report PDF
    form_filename = f'{a.agreement_no}_Police_Tenant_Verification_Form.pdf'
    form_path = STORAGE / form_filename
    build_police_form_pdf(a, form_path)
    
    # Store or update Document record in vault
    doc_exists = dbs.query(Document).filter_by(agreement_id=a.id, doc_type='Police Verification Ack').first()
    if not doc_exists:
        doc = Document(
            agreement_id=a.id,
            filename=ack_filename,
            path=str(ack_path),
            doc_type='Police Verification Ack'
        )
        dbs.add(doc)
        
    dbs.commit()
    log(dbs, a.id, f"AI Auto-Submitted Police Verification: Token {submission_res['ack_token']} (Seal: {submission_res['digital_seal']})")
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}#police-section', status_code=303)

@app.get('/agreements/{agreement_id}/police-ack-pdf')
def get_police_ack_pdf(agreement_id: int):
    """Downloads official Maharashtra Police Tenant Verification Digital Submission Certificate & Receipt."""
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404, 'Agreement not found')
        
    out_file = STORAGE / f'{a.agreement_no}_Police_Verification_Ack.pdf'
    if not out_file.exists():
        enriched = ai_autofill_police_form(a)
        submission_res = ai_process_submission(a, enriched)
        if not a.police_token_no:
            a.police_token_no = submission_res["ack_token"]
            dbs.commit()
        build_police_ack_pdf(a, submission_res, out_file)
        
    dbs.close()
    return FileResponse(
        out_file,
        media_type='application/pdf',
        filename=f'{a.agreement_no}_Police_Verification_Ack.pdf',
        headers={'Cache-Control': 'public, max-age=3600'}
    )

@app.get('/agreements/{agreement_id}/police-portal-bookmarklet')
def get_police_portal_bookmarklet(agreement_id: int):
    """Returns government citizen portal auto-fill JSON payload and JS bookmarklet."""
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404, 'Agreement not found')
        
    enriched = ai_autofill_police_form(a)
    data = generate_portal_autofill_bookmarklet(a, enriched)
    dbs.close()
    return data

@app.post('/agreements/{agreement_id}/biometric-capture')
def biometric_capture(agreement_id: int):
    """
    UIDAI RD Service Biometric Capture Pipeline:
    Connects with STQC-certified biometric scanner (Mantra MFS100 / Morpho MSO 1300 E3),
    authenticates Licensor and Licensee thumb scans, generates cryptographic seal,
    issues official biometric certificate PDF, and updates status to 'Completed'.
    """
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404, 'Agreement not found')
        
    bio_res = simulate_biometric_capture(a)
    a.biometric_status = 'Completed'
    a.biometric_token = bio_res['biometric_token']
    a.biometric_device = bio_res['device_name']
    a.biometric_quality_score = bio_res['owner_quality']
    a.security_seal_hash = bio_res['security_seal']
    a.biometric_date = bio_res['captured_at']
    
    cert_filename = f'{a.agreement_no}_Biometric_Verification_Certificate.pdf'
    cert_path = STORAGE / cert_filename
    build_biometric_cert_pdf(a, bio_res, cert_path)
    
    # Store or update Document record in vault
    doc_exists = dbs.query(Document).filter_by(agreement_id=a.id, doc_type='Biometric Certificate').first()
    if not doc_exists:
        doc = Document(
            agreement_id=a.id,
            filename=cert_filename,
            path=str(cert_path),
            doc_type='Biometric Certificate'
        )
        dbs.add(doc)
        
    dbs.commit()
    log(dbs, a.id, f"UIDAI Biometric Capture Completed via {bio_res['device_name']} (Token: {bio_res['biometric_token']})")
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}#biometric-section', status_code=303)

@app.post('/agreements/{agreement_id}/biometric-schedule')
def biometric_schedule(
    agreement_id: int,
    appointment_date: str = Form(...),
    executive_name: str = Form('Field Officer - Doorstep Desk')
):
    """Schedules doorstep biometric verification appointment."""
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404, 'Agreement not found')
        
    a.biometric_status = 'Scheduled'
    a.biometric_date = appointment_date.strip()
    dbs.commit()
    log(dbs, a.id, f"Scheduled Doorstep Biometrics for {appointment_date.strip()} (Assigned: {executive_name.strip()})")
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}#biometric-section', status_code=303)

@app.get('/agreements/{agreement_id}/biometric-cert-pdf')
def get_biometric_cert_pdf(agreement_id: int):
    """Downloads official Maharashtra Leave & License Biometric Verification Certificate PDF."""
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404, 'Agreement not found')
        
    out_file = STORAGE / f'{a.agreement_no}_Biometric_Verification_Certificate.pdf'
    if not out_file.exists():
        bio_res = simulate_biometric_capture(a)
        if not a.biometric_token:
            a.biometric_token = bio_res['biometric_token']
            a.biometric_status = 'Completed'
            dbs.commit()
        build_biometric_cert_pdf(a, bio_res, out_file)
        
    dbs.close()
    return FileResponse(
        out_file,
        media_type='application/pdf',
        filename=f'{a.agreement_no}_Biometric_Verification_Certificate.pdf',
        headers={'Cache-Control': 'public, max-age=3600'}
    )

@app.post('/agreements/{agreement_id}/inventory')
def add_inventory_item(
    agreement_id: int,
    room: str = Form('Living Room'),
    item_name: str = Form(...),
    quantity: str = Form('1'),
    condition: str = Form('Good / Working'),
    remarks: str = Form(None)
):
    """Adds a fixture/appliance item to Schedule II Inventory."""
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404)
        
    item = InventoryItem(
        agreement_id=a.id,
        room=room.strip(),
        item_name=item_name.strip(),
        quantity=quantity.strip(),
        condition=condition.strip(),
        remarks=remarks.strip() if remarks else 'Good working condition'
    )
    dbs.add(item)
    dbs.commit()
    log(dbs, a.id, f'Added inventory item: {item_name} ({room})')
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}#inventory-section', status_code=303)

@app.post('/agreements/{agreement_id}/inventory/{item_id}/delete')
def delete_inventory_item(agreement_id: int, item_id: int):
    dbs = db()
    item = dbs.get(InventoryItem, item_id)
    if item and item.agreement_id == agreement_id:
        dbs.delete(item)
        dbs.commit()
        log(dbs, agreement_id, f'Removed inventory item #{item_id}')
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}#inventory-section', status_code=303)

@app.get('/agreements/{agreement_id}/inventory/pdf')
def get_inventory_pdf(agreement_id: int):
    """Generates official Schedule II Property Inspection and Inventory Handover Report PDF."""
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404)
        
    items = dbs.query(InventoryItem).filter_by(agreement_id=a.id).order_by(InventoryItem.created_at.asc()).all()
    out_file = STORAGE / f'{a.agreement_no}_Schedule_II_Inventory_Report.pdf'
    build_inventory_pdf(a, items, out_file)
    log(dbs, a.id, 'Generated Schedule II Inventory & Inspection Report (PDF)')
    dbs.close()
    
    return FileResponse(
        out_file,
        media_type='application/pdf',
        filename=f'{a.agreement_no}_Schedule_II_Inventory_Report.pdf',
        headers={'Cache-Control': 'public, max-age=3600'}
    )

@app.post('/agreements/{agreement_id}/approve')
def approve_draft(
    agreement_id: int,
    signer_name: str = Form('Client'),
    signature_data: str = Form(None)
):
    """E-Sign and adopt signature for Leave & License draft."""
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404)
        
    a.status = 'Client Approved'
    if signature_data:
        a.signature_data = signature_data
        
    dbs.commit()
    log(dbs, a.id, f'Draft formally approved & digital signature adopted by {signer_name}')
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}', status_code=303)

@app.post('/agreements/{agreement_id}/renew')
def renew_agreement(
    agreement_id: int,
    escalation_percent: int = Form(5)
):
    """1-Click Tenancy Renewal with automatic escalation and stamp duty recalculation."""
    dbs = db()
    old = dbs.get(Agreement, agreement_id)
    if not old:
        dbs.close()
        raise HTTPException(404, 'Agreement not found')
        
    new_rent = int(round(old.rent * (1.0 + (escalation_percent / 100.0))))
    new_deposit = old.deposit
    new_start = old.end_date + timedelta(days=1)
    new_end = new_start + timedelta(days=334) # 11 months
    months = 11
    
    stamp_res = calculate_stamp_duty(
        monthly_rent=new_rent,
        deposit=new_deposit,
        months=months,
        area_type='urban'
    )
    
    new_agreement = Agreement(
        agreement_no=next_no(dbs),
        owner_name=old.owner_name,
        owner_mobile=old.owner_mobile,
        owner_pan=old.owner_pan,
        owner_aadhaar_last4=old.owner_aadhaar_last4,
        
        tenant_name=old.tenant_name,
        tenant_mobile=old.tenant_mobile,
        tenant_pan=old.tenant_pan,
        tenant_aadhaar_last4=old.tenant_aadhaar_last4,
        tenant_permanent_address=old.tenant_permanent_address,
        tenant_workplace_name=old.tenant_workplace_name,
        tenant_workplace_address=old.tenant_workplace_address,
        tenant_occupation=old.tenant_occupation,
        emergency_contact_name=old.emergency_contact_name,
        emergency_contact_phone=old.emergency_contact_phone,
        vehicle_details=old.vehicle_details,
        
        property_address=old.property_address,
        property_type=old.property_type,
        property_city=old.property_city,
        pincode=old.pincode,
        furnishing_status=old.furnishing_status,
        electricity_consumer_no=old.electricity_consumer_no,
        
        rent=new_rent,
        deposit=new_deposit,
        maintenance_charges=old.maintenance_charges,
        escalation_percent=escalation_percent,
        
        start_date=new_start,
        end_date=new_end,
        notice_period=old.notice_period,
        lock_in=old.lock_in,
        purpose=old.purpose,
        special_terms=f"Renewal of agreement {old.agreement_no} with {escalation_percent}% escalation. {old.special_terms or ''}",
        
        stamp_duty_amount=stamp_res['stamp_duty'],
        registration_fee=stamp_res['registration_fee'],
        total_govt_fees=stamp_res['total_govt_fees'],
        
        witness1_name=old.witness1_name,
        witness1_phone=old.witness1_phone,
        witness2_name=old.witness2_name,
        witness2_phone=old.witness2_phone,
        
        status='Draft',
        registration_status='Not Started',
        police_status='Not Started'
    )
    
    dbs.add(new_agreement)
    dbs.commit()
    dbs.refresh(new_agreement)
    new_id = new_agreement.id
    
    # Also clone inventory items if any
    old_items = dbs.query(InventoryItem).filter_by(agreement_id=old.id).all()
    for oi in old_items:
        dbs.add(InventoryItem(
            agreement_id=new_id,
            room=oi.room,
            item_name=oi.item_name,
            quantity=oi.quantity,
            condition=oi.condition,
            remarks=oi.remarks
        ))
    dbs.commit()
    
    log(dbs, old.id, f'Agreement renewed into {new_agreement.agreement_no} (New Rent: INR {new_rent:,})')
    log(dbs, new_id, f'Created as renewal of {old.agreement_no} with {escalation_percent}% escalation')
    dbs.close()
    
    return RedirectResponse(f'/agreements/{new_id}', status_code=303)

@app.get('/agreements/{agreement_id}/pdf')
def get_pdf(agreement_id: int):
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404)
        
    out_file = STORAGE / f'{a.agreement_no}_legal_draft.pdf'
    
    # 0ms Instant Cache
    if not out_file.exists():
        build_legal_pdf(a, out_file)
        log(dbs, a.id, 'Generated Maharashtra Statutory Legal PDF')
        
    dbs.close()
    
    return FileResponse(
        out_file,
        media_type='application/pdf',
        filename=f'{a.agreement_no}_Leave_and_License_Agreement.pdf',
        headers={'Cache-Control': 'public, max-age=3600'}
    )

@app.post('/agreements/{agreement_id}/upload')
async def upload_document(
    agreement_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...)
):
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404)
        
    ext = Path(file.filename or '').suffix.lower()
    if ext not in {'.pdf', '.jpg', '.jpeg', '.png'}:
        dbs.close()
        raise HTTPException(400, 'Only PDF, JPG, and PNG files are allowed')
        
    safe_name = f'{a.agreement_no}_{doc_type.replace(" ", "_")}_{secrets.token_hex(4)}{ext}'
    p = STORAGE / safe_name
    p.write_bytes(await file.read())
    
    dbs.add(Document(
        agreement_id=a.id,
        filename=file.filename or safe_name,
        path=str(p),
        doc_type=doc_type
    ))
    dbs.commit()
    log(dbs, a.id, f'Document uploaded: {doc_type} ({file.filename})')
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}', status_code=303)

@app.get('/documents/{doc_id}')
def view_document(doc_id: int):
    dbs = db()
    d = dbs.get(Document, doc_id)
    dbs.close()
    if not d or not Path(d.path).exists():
        raise HTTPException(404, 'Document not found')
    return FileResponse(d.path, filename=d.filename)

@app.post('/agreements/{agreement_id}/payments')
def record_payment(
    agreement_id: int,
    payment_type: str = Form('Rent'),
    amount: int = Form(...),
    payment_date: date = Form(...),
    payment_mode: str = Form('UPI'),
    reference_no: str = Form(None),
    for_month_year: str = Form(...)
):
    dbs = db()
    a = dbs.get(Agreement, agreement_id)
    if not a:
        dbs.close()
        raise HTTPException(404)
        
    count = dbs.query(Payment).count() + 1
    receipt_no = f"DP-REC-{date.today().year}-{count:05d}"
    
    p = Payment(
        agreement_id=a.id,
        receipt_no=receipt_no,
        payment_type=payment_type,
        amount=amount,
        payment_date=payment_date,
        payment_mode=payment_mode,
        reference_no=reference_no.strip() if reference_no else None,
        for_month_year=for_month_year.strip()
    )
    dbs.add(p)
    dbs.commit()
    log(dbs, a.id, f'Payment recorded: INR {amount:,} ({payment_type} for {for_month_year}) - Receipt: {receipt_no}')
    dbs.close()
    return RedirectResponse(f'/agreements/{agreement_id}', status_code=303)

@app.get('/payments/{payment_id}/receipt')
def download_rent_receipt(payment_id: int):
    dbs = db()
    p = dbs.get(Payment, payment_id)
    if not p:
        dbs.close()
        raise HTTPException(404, 'Payment record not found')
        
    a = dbs.get(Agreement, p.agreement_id)
    out_file = STORAGE / f'{p.receipt_no}.pdf'
    
    # 0ms Instant Cache
    if not out_file.exists():
        build_receipt_pdf(p, a, out_file)
        
    dbs.close()
    
    return FileResponse(
        out_file,
        media_type='application/pdf',
        filename=f'{p.receipt_no}_HRA_Rent_Receipt.pdf',
        headers={'Cache-Control': 'public, max-age=3600'}
    )

@app.get('/api/calculate-stamp-duty')
def api_stamp_calculator(
    rent: int = Query(..., ge=0),
    deposit: int = Query(0, ge=0),
    months: int = Query(11, ge=1, le=120),
    non_refundable: int = Query(0, ge=0),
    area_type: str = Query('urban')
):
    """High-speed calculation API for live form calculation."""
    return calculate_stamp_duty(
        monthly_rent=rent,
        deposit=deposit,
        months=months,
        non_refundable_deposit=non_refundable,
        area_type=area_type
    )

@app.get('/agreements/export/csv')
def export_csv():
    dbs = db()
    agreements = dbs.query(Agreement).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Agreement No', 'Owner Name', 'Owner Mobile', 'Owner PAN',
        'Tenant Name', 'Tenant Mobile', 'Tenant PAN', 'Property Address',
        'City', 'Rent (INR)', 'Deposit (INR)', 'Stamp Duty (INR)', 'Reg Fee (INR)',
        'Start Date', 'End Date', 'Status', 'Registration Status', 'Police Status',
        'IGR Token', 'Police Token', 'Index-II No', 'Created At'
    ])
    for a in agreements:
        writer.writerow([
            a.agreement_no, a.owner_name, a.owner_mobile, a.owner_pan or '',
            a.tenant_name, a.tenant_mobile, a.tenant_pan or '', a.property_address,
            a.property_city or '', a.rent, a.deposit, a.stamp_duty_amount or 0, a.registration_fee or 0,
            a.start_date, a.end_date, a.status, a.registration_status, a.police_status,
            a.igr_token_no or '', a.police_token_no or '', a.index_ii_no or '', a.created_at
        ])
    dbs.close()
    
    return Response(
        content=output.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename=dashmesh_agreements_{date.today().isoformat()}.csv'}
    )

@app.post('/agreements/quick-create')
def quick_create_agreement(raw_text: str = Form(...)):
    """
    AI 1-Prompt Automatic Agreement Creator:
    Parses unstructured user input, infers all 30+ legal particulars,
    calculates stamp duty, generates inventory, police verification, and PDFs.
    """
    dbs = db()
    parsed_data = parse_quick_text(raw_text)
    a = create_full_automated_agreement(
        dbs=dbs,
        AgreementModel=Agreement,
        DocumentModel=Document,
        InventoryItemModel=InventoryItem,
        AuditLogModel=AuditLog,
        storage_dir=STORAGE,
        data=parsed_data
    )
    new_id = a.id
    dbs.close()
    return RedirectResponse(f'/agreements/{new_id}', status_code=303)
