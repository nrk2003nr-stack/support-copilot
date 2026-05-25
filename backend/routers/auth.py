from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.db.models import Customer, Admin
from backend.core.auth import hash_password, verify_password, create_token
from pydantic import BaseModel

router = APIRouter(prefix='/auth', tags=['auth'])

class RegisterRequest(BaseModel):
    customer_id: str
    name: str
    email: str
    phone_no: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post('/register')
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(Customer).filter(Customer.email == req.email).first():
        raise HTTPException(status_code=400, detail='Email already registered')
    if db.query(Customer).filter(Customer.customer_id == req.customer_id).first():
        raise HTTPException(status_code=400, detail='Customer ID already exists')
    customer = Customer(
        customer_id=req.customer_id,
        name=req.name,
        email=req.email,
        phone_no=req.phone_no,
        password=hash_password(req.password)
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    token = create_token({'sub': customer.customer_id, 'role': 'customer'})
    return {
        'token': token,
        'customer_id': customer.customer_id,
        'name': customer.name,
        'role': 'customer'
    }

@router.post('/login')
def login(req: LoginRequest, db: Session = Depends(get_db)):
    print(f"Login attempt for email: {req.email}")

    # Check customer table
    customer = db.query(Customer).filter(Customer.email == req.email).first()
    if customer:
        print(f"Customer found: {customer.name}, hash starts: {customer.password[:20]}")
        pwd_ok = verify_password(req.password, customer.password)
        print(f"Password verify result: {pwd_ok}")
        if pwd_ok:
            token = create_token({'sub': customer.customer_id, 'role': 'customer'})
            return {
                'token': token,
                'role': 'customer',
                'customer_id': customer.customer_id,
                'name': customer.name
            }
        else:
            raise HTTPException(status_code=401, detail='Invalid credentials')

    # Check admin table
    admin = db.query(Admin).filter(Admin.email == req.email).first()
    if admin:
        print(f"Admin found: {admin.username}")
        pwd_ok = verify_password(req.password, admin.password)
        print(f"Admin password verify: {pwd_ok}")
        if pwd_ok:
            token = create_token({'sub': admin.username, 'role': 'admin'})
            return {
                'token': token,
                'role': 'admin',
                'name': admin.username
            }
        else:
            raise HTTPException(status_code=401, detail='Invalid credentials')

    print("No user found with that email")
    raise HTTPException(status_code=401, detail='Invalid credentials')