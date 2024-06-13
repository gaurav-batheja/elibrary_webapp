from flask import redirect, render_template, request, flash, Flask, url_for
from flask import current_app as app
from flask_login import login_user, LoginManager, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import os
from .model import db,User,Book,Section,Req_book,User_book,logs,review
from werkzeug.utils import secure_filename
import fitz
from datetime import timedelta,date
from dash import Dash, html, dcc, Output
import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

#<-------------------------------------------------------------------------------------------------------------------------->
#<-------------------------------------------------------------------------------------------------------------------------->
#<-------------------------------------------------------------------------------------------------------------------------->
#<-------------------------------------------------------------------------------------------------------------------------->
#<-------------------------------------------------------Dash APP----------------------------------------------------------->


dash_app = Dash(__name__, server=app,url_base_pathname='/dashboard/')

if __name__ == '__main__':
    dash_app.run_server(debug=True, port=8050)

def line_chart():
    #Date vs No. of Issue
    log = db.session.query(logs.book_date_of_issue, logs.req_type).all()
    if log:
    # Preprocess Data
        data = pd.DataFrame(log, columns=['book_date_of_issue', 'req_type'])
        data['book_date_of_issue'] = pd.to_datetime(data['book_date_of_issue']).dt.date
        data = data.groupby(['book_date_of_issue', 'req_type']).size().unstack(fill_value=0)

        fig = px.line(data, x=data.index, y=data.columns, title='Book Issues by Day')
        fig.update_layout(xaxis_title='Date', yaxis_title='Number of Books Issued')
        return fig

#Pie of Issue Type
def pie_chart():
    piedata = db.session.query(logs.req_type, db.func.count(logs.s_no)).group_by(logs.req_type).all()
    data = {'Type': [], 'Count': []}
    for result in piedata:
        if result[0] == 1:
            data['Type'].append("Issue")
            data['Count'].append(result[1])
        else:
            data['Type'].append("Download")
            data['Count'].append(result[1])
    df = pd.DataFrame(data)
    pie = px.pie(df, values='Count', names='Type', title='Total Issues by Type')
    return pie

def pie_books():
    piedata = db.session.query(logs.book_id, db.func.count(logs.s_no)).group_by(logs.book_id).all()
    data = {'Type': [], 'Count': []}
    for result in piedata:
        book = logs.query.filter_by(book_id=result[0]).first()
        if book:
            bookname=book.book_name
            data['Type'].append(bookname)
            data['Count'].append(result[1])
    df = pd.DataFrame(data)
    pie_books = px.pie(df, values='Count', names='Type', title='Book Issue Distribution')
    return pie_books

dash_app.layout = html.Div([
            html.H3(' Total Book Issue vs Day Graph'),
            dcc.Graph(id='my-graph', figure=line_chart()),
            dcc.Graph(id='pie', figure=pie_chart()),
            dcc.Graph(id='pie2', figure=pie_books())
        ])
# @app.route('/dashboard')
# def dashboard():
#     if current_user.is_admin in [1,2]:
#         return render_template('dashboard.html', dash_url='/dashboard')
#     return redirect(url_for("home"))

# def dummylogs():
#     k=1
#     for i in range(3,6,1):
#         k+=1
#         for j in(1,4,2):
#             issue_date=date.today()- timedelta(days=i)
#             return_date=date.today()- timedelta(days=1)
#             book_name = "book" + str(i)
#             log = logs(book_id =k,user_id=i,req_type=1,book_name=book_name,book_date_of_issue=issue_date,book_return_date=return_date)
#             db.session.add(log)
#             db.session.commit()
#<-------------------------------------------------------------------------------------------------------------------------->
#<-------------------------------------------------------------------------------------------------------------------------->
#<-------------------------------------------------------------------------------------------------------------------------->
#<-------------------------------------------------------------------------------------------------------------------------->
#<------------------------------------------------FLASK APP----------------------------------------------------------------->
UPLOAD_FOLDER ='/static/'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

basedir = os.path.abspath(os.path.dirname(__file__))
date_today=date.today()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def autodeletereq(user_id):
    print("running auto delete")
    allreq = Req_book.query.filter_by(user_id=user_id).all()
    if allreq:
        if len(allreq)>5:
            reqs = Req_book.query.filter(Req_book.req_status.in_([1,2]),Req_book.user_id==user_id).all()
            if reqs:
                delreq=len(allreq)%5
                for i in range(delreq):
                    req=reqs[i]
                    db.session.delete(req)
                db.session.commit()

def autoreturn(date_today):
    print("running auto return")
    userbooks=User_book.query.filter_by(req_type=1).all()
    if userbooks:
        for userbook in userbooks:
            if userbook.book_return_date<date_today:
                book = Book.query.filter_by(book_id=userbook.book_id).first()
                user = User.query.filter_by(user_id=userbook.user_id).first()
                inuser=user.user_books.split(",")
                if str(book.book_id) in inuser:
                    inuser.remove(str(book.book_id))
                try:
                    updated_string = ','.join(inuser)
                except:
                    updated_string=""
                user.user_books=updated_string

                bookuserid=book.book_issued_to.split(",")
                if str(user.user_id) in bookuserid:
                    bookuserid.remove(str(user.user_id))
                try:
                    updated_string = ','.join(bookuserid)
                except:
                    updated_string=""
                book.book_issued_to = updated_string
                print(userbook,book.book_issued_to,user.user_books)
                db.session.delete(userbook)
                db.session.commit()
                print(userbook,book.book_issued_to,user.user_books)
 


#-------initiallize login manager--------------
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(id):
    return User.query.get(id)


@app.route("/adminlogin",methods = [ "GET" , "POST"])
def adminlogin():
    if request.method == "GET":
        return render_template('adminlogin.html')
    
    if request.method == "POST":
        name = request.form["adminusername"].strip()
        password = request.form["adminpassword"]
        if name=="":
            flash("Values cannot be null")
            return redirect(url_for("adminlogin"))
        user = User.query.filter_by(user_name=name).first()
        if user and user.is_admin in [1,2]:
                if bcrypt.check_password_hash(user.user_pass,password):
                    login_user(user)
                    return redirect(url_for("admindashboard"))
                else:
                    flash("Incorrect Username/Password")
                    return redirect(url_for("adminlogin"))
        else:
            flash("Access Denied")
            return redirect("/login")
        
@app.route("/addadmin",methods = ['GET','POST'])
@login_required
def addadmin():
    if request.method == "GET":
        if current_user.is_admin == 2:
            return render_template("makeadmin.html")
        elif current_user.is_admin == 1:
            return redirect(url_for("admindashboard"))
        else:
            return redirect(url_for("home"))
        
    if request.method == "POST":
        adminname = request.form["newadminname"]
        newadmin = User.query.filter_by(user_name = adminname).first()
        if newadmin:
            if newadmin.is_admin !=1:
                    newadmin.is_admin = 1
                    flash(newadmin.user_name +" is an Admin now")
                    db.session.commit()
                    return render_template("makeadmin.html")
            flash("Already an Admin")
            return render_template("makeadmin.html")
        else:
            flash("No Such User")
            return render_template("makeadmin.html")
        

@app.route("/deladmin",methods = ['GET','POST'])
@login_required
def deladmin():
    if request.method == "GET":
        if current_user.is_admin == 2:
            return render_template("deladmin.html")
        elif current_user.is_admin == 1:
            return redirect(url_for("admindashboard"))
        else:
            return redirect(url_for("home"))
            
        
    if request.method == "POST":
        adminname = request.form["adminname"].strip()
        if  not adminname:
            flash("Name cannot be blank")
            return render_template("deladmin.html")
        admin = User.query.filter_by(user_name = adminname,is_admin = 1).first()
        if admin:
            admin.is_admin = 0
            db.session.commit()
            flash( admin.user_name + " admin access revoked")
            return render_template("deladmin.html")
        else:
            flash("No Such Admin")
            return render_template("deladmin.html")
        

@app.route("/admindashboard", methods = [ "GET" ])
@login_required
def admindashboard():
    user=current_user
    if request.method == "GET":
        if user.is_admin in [1,2]:
            dash_app.layout = html.Div([
            html.H3(' Total Book Issue vs Day Graph'),
            dcc.Graph(id='my-graph', figure=line_chart()),
            dcc.Graph(id='pie', figure=pie_chart()),
            dcc.Graph(id='pie2', figure=pie_books())
        ])
            return render_template('admindashboard.html',user=user)
        return redirect(url_for('home'))
    

@app.route("/register", methods = [ "GET", "POST" ])
def register():
    if request.method == "GET":
        return render_template("register.html")
    
    if request.method == "POST":
        email = request.form["email"].strip()
        username = request.form["username"].strip()
        existing_email = User.query.filter_by(user_mail = email).first()
        existing_name = User.query.filter_by(user_name = username).first()
        if existing_name or existing_email:
            flash("Name/Email Already Taken, Login to continue")
            return redirect(url_for("register"))
        
        else:
            password = request.form["password"]
            passwordagain = request.form["passwordagain"]
            if email == "" or username == "":
                flash("Values cannot be Blank")
                return redirect(url_for("register"))
            if password == passwordagain:
                hashed_password = bcrypt.generate_password_hash(password)
                new_user = User(mail=email,password=hashed_password,username=username)
                db.session.add(new_user)
                db.session.commit()
            else:
                flash("Opps! Password didnt match")
                return redirect('/register')
            flash("Welcome New Reader, Login to Start your journey")
            return redirect('/login')
        
        
@app.route("/login", methods = [ "GET" , "POST" ])
def login():
    
    if request.method == "GET":
        return render_template('login.html')
    if request.method == "POST":
        name = request.form["loginusername"].strip()
        password = request.form["loginpassword"]
        if name=='' or password=='':
            flash("Cannot be null")
            return redirect(url_for("login"))
        user = User.query.filter_by(user_name=name).first()
        if user:
            if bcrypt.check_password_hash(user.user_pass,password):
                login_user(user)
                return redirect("/")
        flash("Incorrect Username or password")
        return redirect("/login")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/login")


@app.route('/', methods = [ "GET" ])
@login_required
def home():
    # dummylogs()
    user=current_user
    autodeletereq(user.user_id)
    autoreturn(date_today)
    if request.method == "GET":
        primaryadmin = User.query.filter_by(user_name="primaryadmin").first()
        primaryadmin.is_admin = 2
        admin=User.query.filter_by(user_name = "admin1").first()
        admin.is_admin = 1
        db.session.commit()
        # current_datetime = (date.today())
        # future =timedelta(days = 0)
        # future = current_datetime+future
        # print(future<=current_datetime)
        if current_user.is_admin == 0:
            return redirect(url_for("userprofile",user_id=user.user_id))
        return redirect(url_for("admindashboard"))
    

@app.route("/addbook/<int:section_id>", methods = [ "GET","POST"])
@login_required
def addbook(section_id):
    if current_user.is_admin in [1,2]:
        if request.method == "GET":
            if section_id:
                section = Section.query.filter_by(section_id=section_id).first()
                section_name=section.section_name
            else:
                section_name=""
            return render_template("addbook.html",section_name=section_name)
        if request.method == "POST":
            newbook = request.form["book_name"].strip()
            book_author = request.form["book_author"].strip()
            book_section = request.form["book_section"].strip()
            book_pdf_path = request.files["book_pdf_path"]
            book_img_path = request.files["book_img_path"]
            book_desc = request.form["book_desc"]
            book_price = request.form["book_price"]
            if section_id and book_section =="":
                section = Section.query.filter_by(section_id=section_id).first()
                book_section = section.section_name
            basedir = os.path.abspath(os.path.dirname(__file__))

            checkbook = Book.query.filter_by(book_name=newbook).first()
            if checkbook:
                flash("Book Already Added")
                return render_template("addbook.html")
            elif newbook=='' or book_section == '' or book_author =='' or book_pdf_path.filename == '' or book_img_path.filename=='':
                flash("Fields/Files Blank")
                return render_template("addbook.html")
            
            
            if book_pdf_path and allowed_file(book_pdf_path.filename):
                filename1 = secure_filename(book_pdf_path.filename)
                book_pdf_path.save(basedir + "/../static/PDF/" + filename1)
            if book_img_path and allowed_file(book_img_path.filename):
                filename2 = secure_filename(book_img_path.filename)
                book_img_path.save(basedir + "/../static/IMG/" + filename2)
            
            newbook = Book(book_name=newbook,book_section=book_section,book_author=book_author,book_pdf_path=filename1,book_img_path=filename2,book_desc=book_desc,book_price=book_price)
            db.session.add(newbook)

            section = Section.query.filter_by(section_name=book_section).first()
            if section:
                section.section_books=section.section_books + ","+ str(newbook.book_id)
            else:
                flash("Creating Section "+str(book_section))
                
                section = Section(section_name=book_section,section_description="Add Description",section_books=str(newbook.book_id),date_created=date_today)
            db.session.add(section)
            db.session.commit()
            flash("Book Added")
            return redirect(url_for('addbook',section_id=section_id))
    return redirect(url_for('home'))


@app.route("/editbook/<int:book_id>", methods = ['GET','POST'])
@login_required
def editbook(book_id):
    if current_user.is_admin in [1,2]:
        book = Book.query.filter_by(book_id=book_id).first()
        if book:
            if request.method == "GET":
                return render_template("editbook.html",book_name=book.book_name,book_author=book.book_author,book_desc=book.book_desc,book_img_path=book.book_img_path,book_pdf_path=book.book_pdf_path,book_section=book.book_section,book_price=book.book_price)
            if request.method == "POST":
                new_book_name = request.form["book_name"]
                new_book_section = request.form["book_section"]
                new_book_author = request.form["book_author"]
                new_book_pdf_path = request.files["book_pdf_path"]
                new_book_img_path = request.files["book_img_path"]
                new_book_desc = request.form["book_desc"]
                new_book_price = request.form["book_price"]

                if new_book_name != '':
                    book.book_name = new_book_name
                if new_book_author != '':
                    book.book_author = new_book_author
                if new_book_desc != '':
                    book.book_desc = new_book_desc
                if new_book_price != '':
                    book.book_price = int(new_book_price)
                if new_book_section != '':
                
                    section=Section.query.filter_by(section_name=book.book_section).first()
                    if section:
                        int_list = section.section_books.split(",")
                        if str(book.book_id) in int_list:
                            int_list.remove(str(book.book_id))
                        
                        try:
                            updated_string = ','.join(int_list)
                        except:
                            updated_string=""
                        section.section_books = updated_string

                    new_section = Section.query.filter_by(section_name=new_book_section).first()
                    if new_section:
                        new_section.section_books = new_section.section_books + ","+ str(book.book_id) 
                    else:
                        flash("Section Not Found")
                        return redirect(url_for("editbook",book_id=book.book_id ))
                    book.book_section = new_book_section

                # basedir = os.path.abspath(os.path.dirname(__file__))

                if new_book_img_path.filename !='':
                    if new_book_img_path and allowed_file(new_book_img_path.filename):
                        filename2 = secure_filename(new_book_img_path.filename)
                        new_book_img_path.save(basedir + "/../static/IMG/" + filename2)
                    book.book_img_path = filename2
                if new_book_pdf_path.filename !='':
                    if new_book_pdf_path and allowed_file(new_book_pdf_path.filename):
                        filename1 = secure_filename(new_book_pdf_path.filename)
                        new_book_pdf_path.save(basedir + "/../static/PDF/" + filename1)
                    book.book_pdf_path = filename1
                db.session.commit()  
                flash("All changes made")
                return redirect(url_for("editbook", book_id=book.book_id))
        flash("No Such Book")
        return redirect(url_for("addbook"))
    return redirect(url_for("home"))
    

@app.route("/deletebook/<int:book_id>")
@login_required
def deletebook(book_id):
    if current_user.is_admin in [1,2]:
        issued=User_book.query.filter_by(book_id=book_id).first()
        if  not issued:
            book=Book.query.filter_by(book_id=book_id).first()
            if book:
                reqs=Req_book.query.filter_by(book_id=book_id).all()
                for req in reqs:
                    db.session.delete(req)
                section=Section.query.filter_by(section_name=book.book_section).first()
                if section:
                    int_list = section.section_books.split(",")
                    if str(book.book_id) in int_list:
                        int_list.remove(str(book.book_id))
                    try:
                        updated_string = ','.join(int_list)
                    except:
                        updated_string=""
                    section.section_books = updated_string
                basedir = os.path.abspath(os.path.dirname(__file__))
                os.remove(basedir + "/../static/PDF/" + book.book_pdf_path)
                os.remove(basedir + "/../static/IMG/" + book.book_img_path)
                db.session.delete(book)
                db.session.commit()
                flash("BOOK Deleted")
                return redirect(url_for("viewbook"))
        else:
            flash("Books issued to some user")
            return redirect(url_for("viewbook"))
    flash("BOOK NOT FOUND")
    return redirect(url_for("home"))


@app.route("/addsection", methods = [ "GET","POSt" ])
@login_required
def addsection():
    if current_user.is_admin in [1,2]:
        if request.method == "GET":
            return render_template("addsection.html")
        if request.method == "POST":
            section_name=request.form["section_name"].strip()
            section_description=request.form["section_desc"]
            if section_name != '':
                date_today = date.today()
                section = Section(section_name=section_name,section_description=section_description,date_created=date_today)
                db.session.add(section)
                db.session.commit()
                flash("Section Added")
            else:
                flash("Name cannot be Blank")
        return redirect(url_for("addsection"))
    return redirect(url_for("home"))


@app.route("/editsection/<int:section_id>", methods = [ "GET" ,"POST" ])
@login_required
def editsection(section_id):
    if current_user.is_admin  in [1,2]:
        if request.method == "GET":
            section = Section.query.filter_by(section_id=section_id).first()
            return render_template("editsection.html",section=section)
        if request.method == "POST":
            section = Section.query.filter_by(section_id=section_id).first()
            new_section_name=request.form["section_name"]
            check = Section.query.filter_by(section_name=new_section_name).first()
            if check:
                flash("Section Already Exists")
                return redirect(url_for("editsection",section_id=section.section_id))
            new_section_description=request.form["section_desc"]
            if new_section_name == "":
                new_section_name = section.section_name
            if new_section_description== "":
                new_section_description=section.section_description
            section.section_description=new_section_description
            section.section_name=new_section_name
            db.session.commit()
            flash("Section Edited")
            return redirect(url_for("sections"))
    return redirect(url_for("home"))


@app.route("/deletesection/<int:section_id>", methods = [ "GET","POST" ])
@login_required
def deletesection(section_id):
    if current_user.is_admin in [1,2]:
        if request.method == "GET":
            return render_template("deletesection.html",section_id=section_id)
        if request.method == "POST":
            del_book=request.form["del_book"]

            section = Section.query.filter_by(section_id=section_id).first()
            book = Book.query.filter_by(book_section = section.section_name).all()
            print(del_book)
            if del_book == "Open this select menu":
                flash("Select an option to continue")
                return redirect(url_for("deletesection",section_id=section_id))
            elif int(del_book) == 1:
                for b in book:
                    issued=User_book.query.filter_by(book_id=b.book_id).first()
                    if  not issued:
                        reqs=Req_book.query.filter_by(book_id=b.book_id).all()
                        for req in reqs:
                            db.session.delete(req)
                        db.session.delete(b)
                    else:
                        flash("Book Issued To Some User")
                        return redirect(url_for("deletesection",section_id=section_id))
                db.session.delete(section)
                flash("Books and Section Deleted")
                return redirect(url_for("sections"))
            elif int(del_book) == 2:
                for b in book:
                    b.book_section=""
                db.session.delete(section)
                db.session.commit()
                flash("Section Deleted")
                return redirect(url_for("sections"))
    return redirect(url_for("home"))
        


@app.route("/books", methods = [ "GET" ])
def viewbook():
    if request.method == "GET":
        user=current_user
        books=Book.query.all()
        if books:
            books = books[-1::-1]
        userbooks=User_book.query.filter_by(user_id=user.user_id).all()
        userbook_data={}
        emptydict={}
        if userbooks:
            for book in userbooks:
                emptydict[book.book_id] = book.req_type
                userbook_data[user.user_id] = emptydict
        return render_template("books.html",books=books,user=user,userbooks=userbooks,userbook_data=userbook_data)
    
@app.route("/userprofile/<int:user_id>" , methods = ["GET"])
def userprofile(user_id):
    if request.method == "GET":
        user=current_user
        curr_user=current_user
        if user.user_id == user_id:
            book_ids=[]
            userbooks=User_book.query.filter_by(user_id=user.user_id).all()
            userbook_data={}
            for book in userbooks:
                userbook_data[book.book_id] = book.req_type
                book_ids.append(book.book_id)
            books = Book.query.filter(Book.book_id.in_(book_ids)).all()
            totalbooks = len(userbook_data)
            return render_template("reader_profile.html",user_id=user_id,user=user,books=books,userbook_data=userbook_data,curr_user=curr_user,basedir=basedir,totalbooks=totalbooks)
        elif user.is_admin in [1,2]:
            user=User.query.filter_by(user_id=user_id).first()
            curr_user=current_user
            if user:
                book_ids=[]
                userbooks=User_book.query.filter_by(user_id=user.user_id).all()
                userbook_data={}
                for book in userbooks:
                    userbook_data[book.book_id] = book.req_type
                    book_ids.append(book.book_id)
                books = Book.query.filter(Book.book_id.in_(book_ids)).all()
                totalbooks = len(userbook_data)
                return render_template("reader_profile.html",user_id=user_id,user=user,books=books,userbook_data=userbook_data,curr_user=curr_user,totalbooks=totalbooks)
            return redirect(url_for("home"))
        return redirect(url_for("userprofile",user_id=user.user_id))
    
@app.route("/sections", methods = [ "GET" ])
@login_required
def sections():
    if request.method == "GET":
        section=Section.query.all()
        user=current_user
        section = section[-1::-1]
        return render_template("sections.html",section = section,user=user)

@app.route("/sectionbook/<int:section_id>")
def sectionbook(section_id):
    user=current_user
    section= Section.query.filter_by(section_id=section_id).first()
    if section:
        book_list=section.section_books
        book_list=book_list.split(",")
        book_list = [int(b) for b in book_list if b]
        books = Book.query.filter(Book.book_id.in_(book_list)).all()
        if books:
            userbook_data ={}
            books=books[-1::-1]
            return render_template("books.html",books=books,user=user,userbook_data =userbook_data)
    return redirect(url_for("sections"))


        
@app.route("/bookpreview/<int:book_id>")
@login_required
def bookpreview(book_id):
    book = Book.query.filter_by(book_id=book_id).first()
    if book:
        curr_file = fitz.open(basedir + "/../static/pdf/" + book.book_pdf_path)
        pages=[page for page in curr_file]
        curr_page=pages[0]
        return render_template("bookpreview.html",pages=pages,book=book,curr_page=curr_page)
    return redirect(url_for("home"))

@app.route("/nextpage/<int:book_id>/<int:page_no>")
@login_required
def nextpage(book_id,page_no):
    user=current_user
    book = Book.query.filter_by(book_id=book_id).first()
    if book:
        basedir = os.path.abspath(os.path.dirname(__file__))
        curr_file = fitz.open(basedir + "/../static/pdf/" + book.book_pdf_path)
        pages=[page for page in curr_file]
        if str(book.book_id) in user.user_books:
            pass
        else:
            pages=pages[:2:]
            flash("Preview Limit 2 Pages, Issue/Download the book")
        page_no+=1
        if page_no < len(pages):
            curr_page = pages[page_no]
        else:
            curr_page = pages[0]
            page_no=0
        next=True
        prev=True
        if page_no == len(pages)-1:
            next=False
        if page_no == 0:
            prev=False
        return render_template("nextpage.html",pages=pages,book=book,curr_page=curr_page,next=next,prev=prev,page_no=page_no)
    return redirect(url_for("home"))

@app.route("/prevpage/<int:book_id>/<int:page_no>")
@login_required
def prevpage(book_id,page_no):
    user=current_user
    book = Book.query.filter_by(book_id=book_id).first()
    if book:
        basedir = os.path.abspath(os.path.dirname(__file__))
        curr_file = fitz.open(basedir + "/../static/pdf/" + book.book_pdf_path)
        pages=[page for page in curr_file]
        if str(book.book_id) in user.user_books:
            pass
        else:
            pages=pages[:2:]
            flash("Preview Limit 2 Pages, Issue/Download the book")
        page_no-=1
        if page_no < len(pages):
            curr_page = pages[page_no]
            
        else:
            
            curr_page = pages[0]
            page_no=1
        next=True
        prev=True
        if page_no == len(pages)-1:
            next=False
        if page_no == 0:
            prev=False
        return render_template("prevpage.html",pages=pages,book=book,curr_page=curr_page,next=next,prev=prev,page_no=page_no)
    return redirect(url_for("home"))


@app.route("/req/<int:user_id>/<int:req_type>/<int:book_id>" , methods = [ 'GET', 'POST' ])
@login_required
def req(user_id,book_id,req_type,):
    req=Req_book.query.filter_by(user_id=user_id,req_status=0,book_id=book_id).first()
    total=Req_book.query.filter_by(user_id=user_id,req_status=0).all()
    userbook =User_book.query.filter_by(user_id=user_id,book_id=book_id).first()
    forlimit = User_book.query.filter_by(user_id=user_id,req_type=1).all()
    if len(total)>=5:
        flash("cannot have more than 5 pending requests at a time")
        return redirect(url_for("viewbook"))
    print(req)
    if req:
        if req.book_id == book_id and req.req_status == 0:
            flash("Request already sent for this book")
            return redirect(url_for("viewbook"))
    if userbook:
        flash("book already issued")
        return redirect(url_for("viewbook"))
    if len(forlimit) >=5 and req_type == 1:
        flash("Cannot issue more than 5 books, Please return the books you are done reading")
        return redirect(url_for("viewbook"))
    if request.method == "GET":
        user=User.query.filter_by(user_id=user_id).first()
        book=Book.query.filter_by(book_id=book_id).first()
        return render_template("req_book.html",user=user,book=book,req_type=req_type,date_today=date_today)
    if request.method == "POST":
        if req_type ==1:
            day = request.form["returndate"]
        elif req_type ==2:
            day=0
        day=int(day)
        if day < 0:
            flash("Days Cannot be negative")
            return redirect(url_for("req",user_id=user_id,book_id=book_id,req_type=req_type))
        book_return_date=date_today + timedelta(days=day)
        req = Req_book(user_id=user_id,book_id=book_id,req_type=req_type,req_status=0,book_date_of_issue=date_today,book_return_date=book_return_date)
        req.req_date=date_today
        db.session.add(req)
        req.req_description=request.form["req_desc"]
        

        db.session.commit()
        flash("Request Added!")
        return redirect(url_for("viewbook"))


@app.route("/viewreq", methods = ["GET"])
@login_required
def viewreq():
    if request.method == "GET":
        user=current_user
        autodeletereq(user.user_id)
        reqdata={}
        reqs = Req_book.query.all()
        if reqs:
            reqs=reqs[-1::-1]
            for req in reqs:
                book=Book.query.filter_by(book_id=req.book_id).first()
                user1=User.query.filter_by(user_id=req.user_id).first()
                if book and user1:
                    reqdata[req.req_id]=[user1.user_name,book.book_name]
            return render_template("viewreq.html",reqs=reqs,user=user,reqdata=reqdata)
    return redirect(url_for("home"))
    

@app.route("/delreq/<int:req_id>")
@login_required
def delreq(req_id):
    if current_user.is_admin in [1,2]:
        req=Req_book.query.filter_by(req_id=req_id).first()
        if req and req.req_status == 0:
            req.req_status=2
            db.session.commit()
        return redirect(url_for("viewreq"))
    else:
        req=Req_book.query.filter_by(req_id=req_id).first()
        if req and req.req_status == 0:
            db.session.delete(req)
            db.session.commit()
    return redirect(url_for("viewreq"))  

@app.route("/returnbook/<int:book_id>")
@login_required
def returnbook(book_id):
    if current_user.is_admin == 0:
        user=current_user
        userbook=User_book.query.filter_by(book_id=book_id).first()
        if userbook.req_type == 1:
            if userbook:
                book_log = logs.query.filter_by(book_id=book_id).first()
                book_log.book_return_date = date_today
                book = Book.query.filter_by(book_id=book_id).first()

                userbooks=user.user_books.split(",")
                if str(book_id) in userbooks:
                    userbooks.remove(str(book_id))
                try:
                    updated_string = ','.join(userbooks)
                except:
                    updated_string=""
                user.user_books=updated_string

                bookuserid=book.book_issued_to.split(",")
                if str(user.user_id) in bookuserid:
                    bookuserid.remove(str(user.user_id))
                try:
                    updated_string = ','.join(bookuserid)
                except:
                    updated_string=""
                book.book_issued_to = updated_string
                print("here")
                db.session.delete(userbook)
                db.session.commit()
    return redirect(url_for("home"))


@app.route("/revoke/<int:user_id>/<int:book_id>")
@login_required
def revoke(user_id,book_id):
    if current_user.is_admin in [1,2]:
        user=User.query.filter_by(user_id=user_id).first()
        book=Book.query.filter_by(book_id=book_id).first()
        userbook=User_book.query.filter_by(book_id=book_id).first()
        if userbook:
            book_log = logs.query.filter_by(book_id=book_id).first()
            book_log.book_return_date = date_today
            book = Book.query.filter_by(book_id=book_id).first()
            userbooks=user.user_books.split(",")
            if str(book_id) in userbooks:
                userbooks.remove(str(book_id))
            try:
                updated_string = ','.join(userbooks)
            except:
                updated_string=""
            user.user_books=updated_string

            bookuserid=book.book_issued_to.split(",")
            if str(user.user_id) in bookuserid:
                bookuserid.remove(str(user.user_id))
            try:
                updated_string = ','.join(bookuserid)
            except:
                updated_string=""
            book.book_issued_to = updated_string
            db.session.delete(userbook)
            db.session.commit()
            return redirect(url_for("userprofile",user_id=user_id))
    return redirect(url_for("home"))


@app.route("/passreq/<int:req_id>")
@login_required
def passreq(req_id):
    if current_user.is_admin in [1,2]:
        req=Req_book.query.filter_by(req_id=req_id).first()
        if req:
            req.req_status =1

            book_id=req.book_id
            user_id=req.user_id

            book_date_of_issue=req.book_date_of_issue
            book_return_date=req.book_return_date

            book=Book.query.filter_by(book_id=book_id).first()
            book.book_issued_to = book.book_issued_to +","+str(user_id)
            bookname = book.book_name

            user=User.query.filter_by(user_id=user_id).first()
            user.user_books=user.user_books +","+str(book_id)

            userbook=User_book(book_id=book_id,user_id=user_id,book_date_of_issue=book_date_of_issue,book_return_date=book_return_date,req_type=req.req_type)
            log=logs(book_id=book_id,user_id=user_id,book_date_of_issue=book_date_of_issue,book_return_date=book_return_date,req_type=req.req_type,book_name=bookname)
            db.session.add(log)
            db.session.add(userbook)
            db.session.commit()
        return redirect(url_for("viewreq"))
    return redirect(url_for("home"))

@app.route("/allusers/<int:book_id>",methods = ["GET"])
@login_required
def allusers(book_id):
    if request.method == "GET":
        if book_id==0:
            users = User.query.filter_by(is_admin = 0).all()
        else:
            book=Book.query.filter_by(book_id=book_id).first()
            userids=book.book_issued_to.split(",")
            userids=[int(i) for i in userids if i]
            users = User.query.filter(User.user_id.in_(userids)).all()
        return render_template("allusers.html",users=users)

@app.route("/editprofile/<int:user_id>" , methods = ["GET","POST"])
@login_required
def editprofile(user_id):

    user=User.query.filter_by(user_id=user_id).first()
    if user.is_admin == 0:
        if request.method == "GET":
            return render_template("editprofile.html",user=user)
        if request.method == "POST":
            name=request.form["username"].strip()
            pic = request.files["new_pic"]
            email = request.form["email"]
            password =  request.form["password"]
            pass_again =  request.form["passwordagain"]
            if name !='':
                existing_name = User.query.filter_by(user_name = name).first()
                if existing_name:
                    flash("Name Already Taken")
                    return redirect(url_for("editprofile",user_id=user_id))
                user.user_name = name
            if pic.filename !='':
                if pic and allowed_file(pic.filename):
                        filename2 = secure_filename(pic.filename)
                        pic.save(basedir + "/../static/IMG/" + filename2)
                        user.user_profile_pic = filename2
            if email !='':
                check = User.query.filter_by(user_mail=email).first()
                if check:
                    flash("Email Already In Use")
                    return redirect(url_for("editprofile",user_id=user_id))
                user.user_mail = email
            if password !='' and pass_again !='':
                if password == pass_again:
                    hashed_password = bcrypt.generate_password_hash(password)
                    user.user_pass = hashed_password
                else:
                    flash("Password Didn't Match")
                    return redirect(url_for("editprofile",user_id=user_id))
            if (password != '' and pass_again =='' )or (password == '' and pass_again !=''):
                flash("Enter Passwords Twice to change")
                return redirect(url_for("editprofile",user_id=user_id))
            db.session.commit()
            flash("Edits Successful")
            return redirect(url_for("userprofile",user_id=user.user_id))
        
@app.route("/search",methods = ["GET","POST"])
@login_required
def search():
    if request.method == "POST":
        user= current_user
        query = request.form["query"]
        books = Book.query.filter(Book.book_name.ilike(f'%{query}%')).all()
        sections = Section.query.filter(Section.section_name.ilike(f'%{query}%')).all()

        userbooks=User_book.query.filter_by(user_id=user.user_id).all()
        userbook_data={}
        emptydict={}
        for book in userbooks:
            emptydict[book.book_id] = book.req_type
            userbook_data[user.user_id] = emptydict
        if user.is_admin in [1,2]:
            users = User.query.filter(User.user_name.ilike(f'%{query}%')).all()
        else:
            users =''
        return render_template("searchresult.html",books=books,sections=sections,user=user,userbook_data=userbook_data,userbooks=userbooks,users=users)
    
@app.route("/bookreview/<int:user_id>/<int:book_id>" ,methods = ["GET","POST"])
@login_required 
def bookreview(user_id,book_id):
    if current_user.is_admin == 0:
        if request.method == "GET":
            book = Book.query.filter_by(book_id=book_id).first()
            if book:
                check = review.query.filter_by(user_id=user_id,book_name=book.book_name).first()
                if check:
                    flash("Feedback Already Sent For This BOOK")
                    return redirect(url_for("viewbook"))
                return render_template("feedback.html",book=book)

        if request.method == "POST":
            book=Book.query.filter_by(book_id=book_id).first()
            fb = request.form["feedback"].strip()
            if book and fb:
                feed = review(book_name=book.book_name,book_feedback=fb,user_id=user_id)
                db.session.add(feed)
                db.session.commit()
                flash("Feedback Taken, Thank You for your support")
                return redirect(url_for("viewbook"))
            flash("No Such Book")
            return redirect(url_for("viewbook"))
    return redirect(url_for("home"))
    

@app.route("/viewfeedback" ,methods = ["GET","POST"])
@login_required 
def viewfeedback():
    if current_user.is_admin in [1,2]:
        if request.method == "GET":
            feedbacks = review.query.all()
            if feedbacks:
                return render_template("viewfeedback.html",feedbacks=feedbacks)
            flash("No feedbacks")
            return redirect(url_for("home"))
    return redirect(url_for("home"))
