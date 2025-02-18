from distutils.log import info
from tkinter.messagebox import NO
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, UploadFile, File
from itsdangerous import json
from pydantic import EmailStr
from sqlalchemy import desc
from sqlalchemy.orm import Session
from router import oaut
import datetime
from model import user as UserModel
import shutil
from schema import user as UserSchema
from passlib.context import CryptContext
from router import aut
from schema import token
from Db.Db import get_db
from typing import List
import json
from datetime import timedelta
secretFile = open('config/secret.json', 'rt')
file = json.loads(secretFile.read())
router = APIRouter(tags=['User'], prefix='/user')
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post('/signin', response_model=UserSchema.admin_show, summary='User Signin')
def signin(*, db: Session = Depends(get_db), information: UserSchema.user_signin = Body(...), setAdminTrue: bool = Query(False)):
    try:
        password = pwd_context.hash(information.password)
        user = UserModel.user(name=information.name, password=password, username = information.username, admin = setAdminTrue)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except:
        raise HTTPException(status_code=400)


@router.get('/', response_model=List[UserSchema.user_show], summary='All Users Informations')
def getall(*, db: Session = Depends(get_db), get_current_user: token.token_data = Depends(oaut.get_current_user)):
    try:
        if get_current_user.admin:
            users = db.query(UserModel.user).all()
            return users
        else:
            raise HTTPException(status_code=405, detail='not autorized')
    except:
        raise HTTPException(status_code=400)


@router.get('/one', response_model=UserSchema.user_show, summary='One User Informations')
def update(*, db: Session = Depends(get_db), get_current_user: token.token_data = Depends(oaut.get_current_user), id: str = Query(None), username: str = Query(None), national_number: str = Query(None), email: EmailStr = Query(None)):
    try:
        information = ["id", "username", "national_number", "email"]
        print("...........")
        print(locals()["username"])
        if get_current_user.admin:
            for inf in information:
                if locals()[inf] is not None:
                    print(inf)
                    if inf == "id":
                        user = db.query(UserModel.user).filter(
                            UserModel.user.id == locals()[inf]).first()
                    elif inf == "username":
                        user = db.query(UserModel.user).filter(
                            UserModel.user.username == locals()[inf]).first()
                    elif inf == "national_number":
                        user = db.query(UserModel.user).filter(
                            UserModel.user.national_number == locals()[inf]).first()
                    elif inf =="email":
                        user = db.query(UserModel.user).filter(
                            UserModel.user.email == locals()[inf]).first()
                    if user is not None:
                        return user
                    else:
                        raise HTTPException(status_code=404, detail='not found')
        else:
            raise HTTPException(status_code=405, detail='not autorized')
    except:
        raise HTTPException(status_code=400)


@router.get('/me', response_model=UserSchema.user_show, summary='Current User Informations')
def update(*, db: Session = Depends(get_db), get_current_user: token.token_data = Depends(oaut.get_current_user)):
    try:
        user = db.query(UserModel.user).filter(
            UserModel.user.username == get_current_user.username).first()
        return user
    except:
        raise HTTPException(status_code=400)


@router.put('/me', response_model=UserSchema.user_show, summary='Current User Update')
def update(*, db: Session = Depends(get_db), get_current_user: token.token_data = Depends(oaut.get_current_user),  information: UserSchema.update= Body(...), avatar: UploadFile, moreInfo: list = Query([], description='More Information About User')):
        username = get_current_user.username
        if moreInfo:
            moreInfo = json.dumps(moreInfo).encode('utf8')
            db.query(UserModel.user).filter(UserModel.user.username == username).update(
                {'moreInfo': moreInfo}, synchronize_session=False)
        db.query(UserModel.user).filter(UserModel.user.username == username).update(
            information.dict(), synchronize_session=False)
        db.commit()
        user = db.query(UserModel.user).filter(
            UserModel.user.username == username).first()
        if avatar:
            with open(f"{user.username}.png", "wb") as buffer:
                shutil.copyfileobj(avatar.file, buffer)
        return user


@router.delete('/', summary='User Delete')
def delete(*, db: Session = Depends(get_db), get_current_user: token.token_data = Depends(oaut.get_current_user), id: str = Query(None), username: str = Query(None), national_number: str = Query(None), email: EmailStr = Query(None)):
    try:
        if get_current_user.admin:
            information = ["id", "username", "national_number", "email"]
            for inf in information:
                if locals()[inf] is not None:
                    if inf == "id":
                        user = db.query(UserModel.user).filter(
                            UserModel.user.id == locals()[inf]).delete(synchronize_session=False)
                    elif inf == "username":
                        user = db.query(UserModel.user).filter(
                            UserModel.user.username == locals()[inf]).delete(synchronize_session=False)
                    elif inf == "national_number":
                        user = db.query(UserModel.user).filter(
                            UserModel.user.national_number == locals()[inf]).delete(synchronize_session=False)
                    elif inf =="email":
                        user = db.query(UserModel.user).filter(
                            UserModel.user.email == locals()[inf]).delete(synchronize_session=False)
                    if user:
                        db.commit()
                        return 'user deleted'
                    else:
                        raise HTTPException(status_code=404, detail='not found')
            raise HTTPException(status_code=404, detail='not found')
        else:
            raise HTTPException(status_code=405, detail='not autorized')
    except:
        raise HTTPException(status_code=400)


@router.post('/login', response_model=token.token_show, summary='User Login')
def loggin(db: Session = Depends(get_db), information: oaut.OAuth2PasswordRequestForm = Depends()):
    print('aas')
    username = information.username
    password = information.password
    user = db.query(UserModel.user).filter(
        UserModel.user.username == username).first()
    if not user:
        raise HTTPException(detail='not found', status_code=404)
    if not pwd_context.verify(password, user.password):
        print(1)
        raise HTTPException(detail='wrong password', status_code=400)
    access_token_expires = timedelta(
        minutes=file["ACCESS_TOKEN_EXPIRE_MINUTES"])
    access_token = aut.create_access_token(
        data={"sub": f'{user.username}, admincheck:{user.admin}'}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.delete('/logout/all', summary='User Delete Account')
def logout(db: Session = Depends(get_db),  get_current_user: token.token_data = Depends(oaut.get_current_user)):
    try:
        db.query(UserModel.user).filter(UserModel.user.username ==
                                        get_current_user.username).delete(synchronize_session=False)
        db.commit()
        return 'account deleted'
    except:
        raise HTTPException(status_code=400)
