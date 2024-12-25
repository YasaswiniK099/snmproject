from flask import Flask,request,render_template,redirect,url_for,flash,session,send_file
import mysql.connector #module to connect with sql files
from otp import genotp
from cmail import sendmail
from stoken import encode,decode
from flask_session import Session
from io import BytesIO
import flask_excel as excel
import re
app=Flask(__name__)  #specifies the current path of file
excel.init_excel(app)
app.config['SESSION_TYPE']='filesystem'
app.secret_key='Codegnan@2018'
mytdb=mysql.connector.connect(host='localhost',user='root',password='admin',db='snmproject')
Session(app)
@app.route('/')  #base route to generate link
def home():
    return render_template('welcome.html')
@app.route('/create',methods=['GET','POST'])
def create():
    if request.method=='POST':
        print(request.form)
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']
        cpassword=request.form['cpassword']
        cursor=mytdb.cursor()
        cursor.execute('select count(useremail) from users where useremail=%s',[email])
        result=cursor.fetchone()
        print(result)
        if result[0]==0:
            gotp=genotp()
            udata={'username':username,'useremail':email,'password':password,'otp':gotp}
            subject='OTP For Simple Notes Manager'
            body=f'otp for registeration of simple notes manager {gotp}'
            sendmail(to=email,subject=subject,body=body)
            flash('OTP has send to given mail')
            return redirect(url_for('otp',enudata=encode(data=udata)))
        elif result[0]>0:
            flash('Email already existed')
            return redirect(url_for('login'))
        else:
            return 'Something went wrong'
    return render_template('create.html') 
@app.route('/otp/<enudata>',methods=['GET','POST'])
def otp(enudata):
    if request.method=='POST':
        uotp=request.form['otp']
        try:
           dudata=decode(data=enudata) #dudata={'username':username,'useremail':email,'password':password}
        except Exception as e:
            print(e)
            return 'Something went wrong'
        else:
            if dudata['otp']==uotp:
                cursor=mytdb.cursor()
                cursor.execute('insert into users(user_name,useremail,password) values(%s,%s,%s)',[dudata['username'],dudata['useremail'],dudata['password']])
                mytdb.commit()
                cursor.close()
                flash('Registration successfull')
                return redirect(url_for('login'))
            else:
                return 'OTP was wrong please register again'
    return render_template('otp.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if not session.get('user'):
        if request.method=='POST':
            uemail=request.form['email']
            upassword=request.form['password']
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select count(useremail) from users where useremail=%s',[uemail])
            bdata=cursor.fetchone() #(1,)
            if bdata[0]==1:
                cursor.execute('select password from users where useremail=%s',[uemail])
                bpassword=cursor.fetchone() #( 0x3132330000000000000000000)
                if upassword==bpassword[0].decode('utf-8'):
                    session['user']=uemail
                    print(session)
                    return redirect(url_for('dashboard'))
                else:
                    flash('password was wrong')
                    return redirect(url_for('login'))
            elif bdata[0]==0:
                flash('Email not existed')
                return redirect(url_for('create'))
            else:
                return 'Something went wrong'
        return render_template('login.html')
    else:
        return redirect(url_for('dashboard'))
@app.route('/dashboard')
def dashboard():
    if session.get('user'):
        return render_template('dashboard.html')
    else:
        return redirect(url_for('login'))
@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    if session.get('user'):
        if request.method=='POST':
            title=request.form['title']
            description=request.form['description']
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select user_id from users where useremail=%s',[session.get('user')])
            uid=cursor.fetchone()
            if uid:
                cursor.execute('insert into notes(title,n_description,user_id) values(%s,%s,%s)',[title,description,uid[0]])
                mytdb.commit()
                cursor.close()
                flash('Notes added successfully')
                return redirect(url_for('dashboard'))
            else:
                return 'something went wrong'  
        return render_template('addnotes.html')
    else:
        return redirect(url_for('login'))
@app.route('/viewallnotes')
def viewallnotes():
    if session.get('user'):
        try:
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select user_id from users where useremail=%s',[session.get('user')])
            uid=cursor.fetchone() #(1,)
            cursor.execute('select n_id,title,create_at from notes where user_id=%s',[uid[0]])
            ndata=cursor.fetchall() #[(1,'python','2024-12-16',11:25:12)]
        except Exception as e:
            print(e)
            flash('No data found')
            return redirect(url_for('dashboard'))
        else:
            return render_template('viewallnotes.html',ndata=ndata)
    else:
        return redirect(url_for('login'))    
@app.route('/viewnotes/<nid>')
def viewnotes(nid):
    if session.get('user'):
        try:
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select * from notes where n_id=%s',[nid])
            ndata=cursor.fetchone()
        except Exception as e:
            print(e)
            flash('No data found')
            return redirect(url_for('dashboard'))
        else:
            return render_template('viewnotes.html',ndata=ndata)
    else:
        return redirect(url_for('login'))    
@app.route('/updatenotes/<nid>',methods=['GET','POST'])
def updatenotes(nid):
    cursor=mytdb.cursor(buffered=True)
    cursor.execute('select *from notes where n_id=%s',[nid])
    ndata=cursor.fetchone()
    if request.method=='POST':
        title=request.form['title']
        description=request.form['description']
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('update notes set title=%s,n_description=%s where n_id=%s',[title,description,nid])
        mytdb.commit()
        cursor.close()
        flash('notes updated successfully')
        return redirect(url_for('viewnotes',nid=nid))
    return render_template('updatenotes.html',ndata=ndata) 
@app.route("/deletenotes/<nid>")
def deletenotes(nid):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('delete from notes where n_id=%s',[nid])
        mytdb.commit()
        cursor.close()
    except Exception as e:
        print(e)    
        flash('could not delete this notes')
        return redirect(url_for('viewallnotes'))
    else:
        flash('Notes deleted successfully')
        return redirect(url_for('viewallnotes')) 
@app.route('/uploadfile',methods=['GET','POST'])
def uploadfile():
    if session.get('user'):
        if request.method=='POST':
            filedata=request.files['file']
            fname=filedata.filename
            fdata=filedata.read()
            try:    
                cursor=mytdb.cursor(buffered=True)
                cursor.execute('select user_id from users where useremail=%s',[session.get('user')])
                uid=cursor.fetchone() #(1,)
                cursor.execute('insert into filedata(filename,fdata,added_by) values(%s,%s,%s)',[fname,fdata,uid[0]])
                mytdb.commit()
            except Exception as e:
                print(e)
                flash("Couldn't upload this file")
                return redirect(url_for('dashboard'))
            else:
                flash('file uploaded successfully')
                return redirect(url_for('dashboard'))  
        return render_template('uploadfile.html')
    else:
        return redirect(url_for('login'))
@app.route('/viewallfiles')
def viewallfiles():
    if session.get('user'):
        try:
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select user_id from users where useremail=%s',[session.get('user')])
            uid=cursor.fetchone() #(1,)
            cursor.execute('select fid,filename,created_at from filedata where added_by=%s',[uid[0]])
            fdata=cursor.fetchall() #[(1,'key.py','2024-12-16',11:25:12)]
        except Exception as e:
            print(e)
            flash('No data found')
            return redirect(url_for('dashboard'))
        else:
            return render_template('viewallfiles.html',fdata=fdata)
    else:
        return redirect(url_for('login'))      
@app.route('/viewfile/<fid>')
def viewfile(fid):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select filename,fdata from filedata where fid=%s',[fid])
        fdata=cursor.fetchone()
        bytes_data=BytesIO(fdata[1])
        return send_file(bytes_data,download_name=fdata[0],as_attachment=False)
    except Exception as e:
        print(e)
        flash("couldn't open file")
        return redirect(url_for('dashboard'))
@app.route('/downloadfile/<fid>')
def downloadfile(fid):
    try:    
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('select filename,fdata from filedata where fid=%s',[fid])
        fdata=cursor.fetchone()
        bytes_data=BytesIO(fdata[1])
        return send_file(bytes_data,download_name=fdata[0],as_attachment=True)
    except Exception as e:
        print(e)
        flash("couldn't download file")
        return redirect(url_for('dashboard')) 
@app.route("/deletefile/<fid>")
def deletefile(fid):
    try:
        cursor=mytdb.cursor(buffered=True)
        cursor.execute('delete from filedata where fid=%s',[fid])
        mytdb.commit()
        cursor.close()
    except Exception as e:
        print(e)    
        flash('could not delete this file')
        return redirect(url_for('viewallfiles'))
    else:
        flash('Notes deleted successfully')
        return redirect(url_for('viewallfiles'))
@app.route('/getexceldata')
def getexceldata():
    if session.get('user'):
        try:
            cursor=mytdb.cursor(buffered=True)
            cursor.execute('select user_id from users where useremail=%s',[session.get('user')])
            uid=cursor.fetchone() #(1,)
            cursor.execute('select n_id,title,n_description,create_at from notes where user_id=%s',[uid[0]])
            ndata=cursor.fetchall() #[(1,'python','2024-12-16',11:25:12)]
        except Exception as e:
            print(e)
            flash('No data found')
            return redirect(url_for('dashboard'))
        else:
            array_data=[list(i) for i in ndata]
            columns=['Notes_id','Title','Content','Created_time']
            array_data.insert(0,columns)
            return excel.make_response_from_array(array_data,'xlsx',fname='notesdata')
    else:
        return redirect(url_for('login'))      
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('home'))
    else:
        return redirect(url_for('login'))
@app.route('/search',methods=['GET','POST'])
def search():
    if session.get('user'):
        try:
            if request.method=='POST':
                sdata=request.form['sname']
                strg=['A-Za-z0-9']
                pattern=re.compile(f'^{strg}',re.IGNORECASE)
                if (pattern.match(sdata)):
                    cursor=mytdb.cursor(buffered=True)
                    cursor.execute('select * from notes where n_id like %s or title like %s or n_description like %s or create_at like %s',[sdata+'%',sdata+'%',sdata+'%',sdata+'%'])
                    sdata=cursor.fetchall()
                    cursor.close()
                    return render_template('dashboard.html',sdata=sdata)
                else:
                    flash('No Data Found')
                    return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('dashboard'))
        except Exception as e:
            print(e)
            flash("can't find anything")
            return redirect(url_for('dashboard'))
    else:
        return render_template(url_for('login'))                       
app.run(use_reloader=True,debug=True)