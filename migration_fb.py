from sqlalchemy.orm import Session
from datetime import datetime, timezone

import firebase_admin
import streamlit as st
from firebase_admin import firestore, credentials

from database import engine, User, Contract

# Application Default credentials are automatically created.

cred = credentials.Certificate(dict(st.secrets["firebase"]))
app = firebase_admin.initialize_app(cred)
db = firestore.client()

# user_ref = [x.to_dict() for x in db.collection("users").get()]

data = list()

# print(json.dumps(data, indent=2))


with Session(bind=engine) as session:
    contratos = {c.name: c.id_contract for c in session.query(Contract).all()}
    for elemento in db.collection('users').get():
        data.append(
            {
                'name': elemento.get("name").lower().strip(),
                'approved': elemento.get("approved"),
                'contract': contratos.get(elemento.get("contract").upper()),
                'created_at': datetime.fromtimestamp(elemento.get("created_at").timestamp(), tz=timezone.utc),
                'email': elemento.get('email').lower(),
                'password': elemento.get('hash'),
                'role': elemento.get('role')
            }
        )
    users = [User(**x) for x in data]
    session.add_all(users)
    session.commit()
