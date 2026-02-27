import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import bcrypt

print('start')
cred = credentials.Certificate(dict(st.secrets["firebase"]))
print('got cred')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
    print('initialized firebase')
db = firestore.client()

# try fetching a single user document instead of streaming entire collection
print('Attempting simple lookup...')
try:
    doc = db.collection('users').document('test@example.com').get()
    print('Lookup result exists:', doc.exists)
    if doc.exists:
        print('Document data:', doc.to_dict())
except Exception as e:
    print('Lookup failed with exception:', e)

# create or ensure a test user exists
test_email = 'test@example.com'
ref = db.collection('users').document(test_email)
try:
    existing = ref.get()
    if not existing.exists:
        hashed = bcrypt.hashpw('password123'.encode(), bcrypt.gensalt()).decode()
        ref.set({'name': 'Tester', 'email': test_email, 'hash': hashed, 'role': 'user', 'contract': 'ABILITY_SJ', 'created_at': firestore.SERVER_TIMESTAMP, 'approved': True})
        print('Created test user')
    else:
        print('Test user already exists')
except Exception as e:
    print('Error accessing test user document:', e)

# attempt login with correct password
try:
    user_doc = ref.get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        senha_hash = user_data['hash'].encode()
        ok = bcrypt.checkpw('password123'.encode(), senha_hash)
        print('checkpw result', ok)
    else:
        print('user not found')
except Exception as e:
    print('Login check failed:', e)
