from .database import db
from flask_login import UserMixin

class User(db.Model,UserMixin):
    __tablename__ = "user"
    user_id=db.Column(db.Integer, primary_key = True, autoincrement = True)
    user_mail=db.Column(db.String(30), nullable = False, unique =True)
    
    user_pass=db.Column(db.String(30), nullable = False)
    user_name=db.Column(db.String(30),nullable= False, unique = True)
    user_profile_pic=db.Column(db.String, default = "user_profile_dummy.jpg")
    user_books=db.Column(db.String , default='') #comma seperated book id
    is_admin=db.Column(db.Integer, default = 0, nullable = False)    
    def __init__(self,mail,password,username):
        self.user_mail=mail
        self.user_pass=password
        self.user_name=username

    def get_id(self):
        return self.user_id
    

class Section(db.Model):
    __tablename__ = "section"
    section_id = db.Column(db.Integer(), primary_key = True , autoincrement = True)
    section_name = db.Column(db.String(20), nullable = False, unique = True)
    
    section_description = db.Column(db.String(50))
    section_books = db.Column(db.String, default='') #comma seperated book id
    date_created = db.Column(db.Date)
    
    def __init__(self,section_name,section_description,section_books,date_created):
        self.section_name = section_name
        self.section_description = section_description
        self.date_created = date_created
        self.section_books=section_books

class Book(db.Model):
    __tablename__ = "book"
    book_id = db.Column(db.Integer(), primary_key = True , autoincrement = True)
    book_name = db.Column(db.String(20), nullable = False, unique = True)
    
    book_author = db.Column(db.String(), nullable = False)
    book_section = db.Column(db.String(), db.ForeignKey('section.section_name'))

    book_img_path = db.Column(db.String)
    book_pdf_path = db.Column(db.String, nullable = False)
    book_desc = db.Column(db.String(150))

    book_issued_to = db.Column(db.String(), default='') #comma seperated user_id
    book_price = db.Column(db.Integer , default = 0)




    def __init__(self,book_name,book_author,book_section,book_img_path,book_pdf_path,book_desc,book_price):
        self.book_name = book_name
        self.book_author = book_author
        self.book_section = book_section
        self.book_img_path = book_img_path
        self.book_pdf_path = book_pdf_path
        self.book_desc=book_desc
        self.book_price=book_price




class Req_book(db.Model):
    __tablename__ = "req_book"
    req_id = db.Column(db.Integer, primary_key = True , autoincrement = True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.user_id'), nullable = False)
    book_id = db.Column(db.Integer(), db.ForeignKey('book.book_id'), nullable = False)
    req_type = db.Column(db.Integer(), nullable = False)
    req_date = db.Column(db.Date)
    req_status = db.Column(db.Integer(), nullable = False)
    req_description = db.Column(db.String(50))
    

    book_date_of_issue = db.Column(db.Date ,nullable = False )
    book_return_date = db.Column(db.Date,nullable = False) 

    def __init__(self,user_id,book_id,req_type,req_status,book_date_of_issue,book_return_date):
        self.user_id=user_id
        self.book_id=book_id
        self.req_type=req_type
        self.req_status=req_status
        self.book_date_of_issue=book_date_of_issue
        self.book_return_date=book_return_date

class User_book(db.Model):
    __tablename__ = "user_book"
    s_no=db.Column(db.Integer(),primary_key = True,autoincrement = True)
    book_id = db.Column(db.Integer(), db.ForeignKey('book.book_id'), nullable=False)
    user_id = db.Column(db.Integer(),db.ForeignKey('user.user_id'), nullable=False)
    req_type = db.Column(db.Integer, db.ForeignKey('req_book.req_type') , nullable = False)

    book_date_of_issue = db.Column(db.Date , db.ForeignKey('req_book.book_date_of_issue') , nullable = False)
    book_return_date = db.Column(db.Date , db.ForeignKey('req_book.book_date_of_issue'), nullable = False) 

class logs(db.Model):
    __tablename__ = "logs"
    s_no=db.Column(db.Integer(),primary_key = True,autoincrement = True)
    book_id = db.Column(db.Integer(), db.ForeignKey('req_book.book_id'), nullable=False)
    user_id = db.Column(db.String ,db.ForeignKey('req_book.user_id'), nullable = False)
    req_type = db.Column(db.Integer, db.ForeignKey('req_book.req_type') , nullable = False)
    book_name= db.Column(db.String, db.ForeignKey('book.book_name'), nullable= False)
    book_date_of_issue = db.Column(db.Date , db.ForeignKey('req_book.book_date_of_issue'), nullable = False)
    book_return_date = db.Column(db.Date , db.ForeignKey('req_book.book_return_date'), nullable = False)

class review(db.Model):
    __tablename__ = "review"
    s_no=db.Column(db.Integer(),primary_key= True,autoincrement = True)
    user_id = db.Column(db.String ,db.ForeignKey('user.user_id'), nullable = False)
    book_name= db.Column(db.String, db.ForeignKey('book.book_name'), nullable= False)
    book_feedback = db.Column(db.String(150), nullable = False)

    def __init__(self,user_id,book_name,book_feedback):
        self.user_id = user_id
        self.book_name = book_name
        self.book_feedback = book_feedback
