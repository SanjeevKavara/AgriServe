from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import mysql.connector
import os
import datetime
from geopy.distance import geodesic
import numpy as np
import folium
from sklearn.cluster import OPTICS
from sklearn.preprocessing import StandardScaler
from flask_socketio import SocketIO, emit, join_room, leave_room
from engineio.payload import Payload
Payload.max_decode_packets = 200
from werkzeug.utils import secure_filename


app = Flask(__name__, static_url_path='/static')
app.secret_key = 'abcdef'

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    charset="utf8",
    use_pure=True,
    database="agri"
)

UPLOAD_FOLDER = 'static/upload'
ALLOWED_EXTENSIONS = { 'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


socketio = SocketIO(app)


_users_in_room = {} # stores room wise user list
_room_of_sid = {} # stores room joined by an used
_name_of_sid = {} # stores display name of users


@app.route('/',methods=['POST','GET'])
def index():

    
    return render_template('index.html')

@app.route('/login',methods=['POST','GET'])
def login():

    msg=""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mydb.cursor()
        cursor.execute('SELECT * FROM farmer WHERE username = %s AND password = %s AND action = 1', (username, password))
        account = cursor.fetchone()
        
        if account:
            session['username'] = username
            session['user_type'] = 'farmer'
            msg="success"  
        else:
            msg="fail"

    return render_template('login.html', msg=msg)




@app.route('/register',methods=['POST','GET'])
def register():
    
    msg=""
    if request.method=='POST':
        name=request.form['name']
        address=request.form['address']
        mobile=request.form['mobile']
        email=request.form['email']
        username=request.form['username']
        password=request.form['password']
        longitude=request.form['longitude']
        latitude=request.form['latitude']
        now = datetime.datetime.now()
        reg_date=now.strftime("%Y-%m-%d")
        
        mycursor = mydb.cursor()
        mycursor.execute("SELECT count(*) FROM farmer where username=%s",(username, ))
        cnt = mycursor.fetchone()[0]
        if cnt==0:
            mycursor.execute("SELECT max(id)+1 FROM farmer")
            maxid = mycursor.fetchone()[0]
            if maxid is None:
                maxid=1
            sql = "INSERT INTO farmer(id, name, address, mobile, email, username, password, reg_date, longitude, latitude) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            val = (maxid, name, address, mobile, email, username, password, reg_date, longitude, latitude)
            mycursor.execute(sql, val)
            mydb.commit()

            msg="success"
        else:
            msg="fail"
  
    return render_template('register.html', msg=msg)


@app.route('/login1',methods=['POST','GET'])
def login1():

    msg=""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mydb.cursor()
        cursor.execute('SELECT * FROM user WHERE username = %s AND password = %s AND action = 1', (username, password))
        account = cursor.fetchone()
        
        if account:
            session['username'] = username
            session['user_type'] = 'user'
            msg="success"  
        else:
            msg="fail"

    
    return render_template('login1.html', msg=msg)




@app.route('/admin',methods=['POST','GET'])
def admin():

    msg=""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mydb.cursor()
        cursor.execute('SELECT * FROM admin WHERE username = %s AND password = %s', (username, password))
        account = cursor.fetchone()
        
        if account:
            session['username'] = username
            session['user_type'] = 'admin'
            msg="success"  
        else:
            msg="fail"

    
    return render_template('admin.html', msg=msg)




@app.route('/register1',methods=['POST','GET'])
def register1():
    
    msg=""
    if request.method=='POST':
        name=request.form['name']
        address=request.form['address']
        mobile=request.form['mobile']
        email=request.form['email']
        username=request.form['username']
        password=request.form['password']
        longitude=request.form['longitude']
        latitude=request.form['latitude']
        now = datetime.datetime.now()
        reg_date=now.strftime("%Y-%m-%d")
        
        mycursor = mydb.cursor()
        mycursor.execute("SELECT count(*) FROM user where username=%s",(username, ))
        cnt = mycursor.fetchone()[0]
        if cnt==0:
            mycursor.execute("SELECT max(id)+1 FROM user")
            maxid = mycursor.fetchone()[0]
            if maxid is None:
                maxid=1
            sql = "INSERT INTO user(id, name, address, mobile, email, username, password, reg_date, longitude, latitude) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            val = (maxid, name, address, mobile, email, username, password, reg_date, longitude, latitude)
            mycursor.execute(sql, val)
            mydb.commit()

            msg="success"
        else:
            msg="fail"
  
    return render_template('register1.html', msg=msg)


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/post', methods=['POST', 'GET'])
def post():
    if 'username' not in session or session.get('user_type') != 'farmer':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login'))
    
    dt=""
    food_type=None
    post_id=None
    username = session.get('username')
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM farmer WHERE username = %s", (username,))
    data = cursor.fetchone()
    cursor.close()
    name=data[1]
    address=data[2]
    mobile=data[3]
    longitude=data[9]
    latitude=data[10]
    
    msg=""
    nearby_users = []
    num_nearby_users = 0
    provider_coords = None  # Initialize with a default value
    if request.method=='POST':
        product_type=request.form['product_type']
        product=request.form['product']
        price=request.form['price']
        quantity=request.form['quantity']
        message=request.form['message']
        if 'image' in request.files:
            image = request.files['image']

            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = 'D:/agriecom/static/uploads/' + filename
                image.save(image_path)
        
                now = datetime.datetime.now()
                post_date=now.strftime("%B %d, %Y")
                post_time=now.strftime("%I:%M %p")
        
                mycursor = mydb.cursor()
        
                mycursor.execute("SELECT max(id)+1 FROM post")
                maxid = mycursor.fetchone()[0]
                if maxid is None:
                    maxid=1
                sql = "INSERT INTO post(id, product_type, product, price, message, name, address, mobile, post_date, post_time, username, longitude, latitude, quantity, image) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                val = (maxid, product_type, product, price, message, name, address, mobile, post_date, post_time, username, longitude, latitude, quantity, filename)
                mycursor.execute(sql, val)
                mydb.commit()

                msg="success"

        

                try:
                    provider_cursor = mydb.cursor(dictionary=True)
                    provider_cursor.execute("SELECT * FROM farmer WHERE username = %s", (username,))
                    provider_data = provider_cursor.fetchone()
                    provider_cursor.close()

                    # Extract provider coordinates
           
                    provider_coords = (provider_data['latitude'], provider_data['longitude'])

                    print("Provider Coordinates:", provider_coords)

                    # Fetch all users with valid latitude and longitude
                    user_cursor = mydb.cursor(dictionary=True)
                    user_cursor.execute("SELECT username, latitude, longitude FROM user WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
                    all_users = user_cursor.fetchall()
                    user_cursor.close()

                    for user in all_users:
                        user_coords = (user['latitude'], user['longitude'])
                        distance = geodesic(provider_coords, user_coords).kilometers


                        if distance < 100:  # Adjust the distance threshold as needed
                            user_details = get_user_details(user['username'])  # Fetch additional details
                            if user_details:
                                nearby_users.append({
                                    'username': user['username'],
                                    'latitude': user['latitude'],
                                    'longitude': user['longitude'],
                                    'user_details': user_details 
                                }) 

                    # Count the number of nearby users
                    num_nearby_users = len(nearby_users)

                except Exception as e:
                    print(f"An error occurred: {e}")
    

    return render_template('post.html', msg=msg, nearby_users=nearby_users, num_nearby_users=num_nearby_users, provider_coords=provider_coords, username=username)



def get_user_details(username):
    try:
        user_cursor = mydb.cursor(dictionary=True)
        user_cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
        user_details = user_cursor.fetchone()
        user_cursor.close()
        return user_details
    except Exception as e:
        print(f"An error occurred while fetching user details: {e}")
        return None




@app.route('/view_post', methods=['POST', 'GET'])
def view_post():
    if 'username' not in session or session.get('user_type') != 'user':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login1'))

    
    dt=""
    food_type=None
    post_id=None
    msg=""
    username = session.get('username')
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
    data = cursor.fetchone()
    cursor.close()
    name=data[1]
    address=data[2]
    mobile=data[3]
    longitude=data[9]
    latitude=data[10]

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM post")
    data5 = cursor.fetchall()
    cursor.close()

    act=request.args.get("act")
    

    if act=="call":
        
        pid=request.args.get("pid")
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM post WHERE id = %s", (pid,))
        data8 = cursor.fetchone()
        cursor.close()
        far_username=data8[10]
        product=data8[2]
        now = datetime.datetime.now()
        req_date=now.strftime("%B %d, %Y")
        
        mycursor = mydb.cursor()
        mycursor.execute("SELECT max(id)+1 FROM request")
        maxid = mycursor.fetchone()[0]
        if maxid is None:
            maxid=1
        sql = "INSERT INTO request(id, username, far_username, product, req_date) VALUES (%s, %s, %s, %s, %s)"
        val = (maxid, username, far_username, product, req_date)
        mycursor.execute(sql, val)
        mydb.commit()
        msg="success"

    else:

        msg="fail"

    if act=="ok":
        
        pid=request.args.get("pid")
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM post WHERE id = %s", (pid,))
        data6 = cursor.fetchone()
        cursor.close()
        far_username=data6[10]
        product=data6[2]
        price=data6[4]
        far_mobile=data6[7]
        pid=data6[0]
        now = datetime.datetime.now()
        req_date=now.strftime("%B %d, %Y")
        
        
        mycursor = mydb.cursor()
        mycursor.execute("SELECT max(id)+1 FROM book")
        maxid = mycursor.fetchone()[0]
        if maxid is None:
            maxid=1
        sql = "INSERT INTO book(id, far_username, product, price, far_mobile, mobile, username, req_date, pid) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        val = (maxid, far_username, product, price, far_mobile, mobile, username, req_date, pid)
        mycursor.execute(sql, val)
        mydb.commit()
        msg="success1"

        session['maxid'] = maxid

        
        return redirect(url_for('quantity', maxid=maxid))
    else:
        msg="fail1"
        
        
    
    msg=""
    nearby_users = []
    num_nearby_users = 0
    provider_coords = None  # Initialize with a default value
    if request.method=='POST':
        search=request.form['search']
        
        try:
            provider_cursor = mydb.cursor(dictionary=True)
            provider_cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
            provider_data = provider_cursor.fetchone()
            provider_cursor.close()

            # Extract provider coordinates
           
            provider_coords = (provider_data['latitude'], provider_data['longitude'])

            print("Provider Coordinates:", provider_coords)

            # Fetch all users with valid latitude and longitude
            user_cursor = mydb.cursor(dictionary=True)
            user_cursor.execute("SELECT username, latitude, longitude FROM post WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND product=%s", (search,))
            all_users = user_cursor.fetchall()
            user_cursor.close()

            for user in all_users:
                user_coords = (user['latitude'], user['longitude'])
                distance = geodesic(provider_coords, user_coords).kilometers


                if distance < 100:  # Adjust the distance threshold as needed
                    user_details = get_post_details(user['username'])  # Fetch additional details
                    if user_details:
                        nearby_users.append({
                            'username': user['username'],
                            'latitude': user['latitude'],
                            'longitude': user['longitude'],
                            'user_details': user_details 
                        }) 

            # Count the number of nearby users
            num_nearby_users = len(nearby_users)

        except Exception as e:
            print(f"An error occurred: {e}")

    return render_template('view_post.html', post=data5, msg=msg, nearby_users=nearby_users, num_nearby_users=num_nearby_users, provider_coords=provider_coords, username=username)



def get_post_details(username):
    try:
        user_cursor = mydb.cursor(dictionary=True)
        user_cursor.execute("SELECT * FROM post WHERE username = %s", (username,))
        user_details = user_cursor.fetchone()
        user_cursor.close()
        return user_details
    except Exception as e:
        print(f"An error occurred while fetching user details: {e}")
        return None


@app.route('/quantity', methods=['GET', 'POST'])
def quantity():
    if 'username' not in session or session.get('user_type') != 'user':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login1'))

    
    maxid=session.get('maxid')

    if request.method=='POST':
        maxid=request.form['maxid']
        quantity=request.form['quantity']
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM book where id = %s",(maxid,))
        data1 = cursor.fetchone()
        cursor.close()
        price=data1[3]

        quantity = int(quantity)
        price = float(price)

        total=quantity*price
        
        cursor = mydb.cursor()
        cursor.execute("update book set quantity=%s, total=%s where id=%s",(quantity, total, maxid))
        mydb.commit()
        return redirect(url_for('payment', maxid=maxid))

    return render_template('quantity.html', maxid=maxid)




@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'username' not in session or session.get('user_type') != 'user':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login1'))

    msg=""
    total=""
    st=""
    mess=""
    mobile=""
    name=""
    maxid=session.get('maxid')
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM book where id = %s",(maxid,))
    data1 = cursor.fetchone()
    cursor.close()
    total=data1[10]
    pid=data1[12]
    quantity1=data1[9]

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM post where id = %s",(pid,))
    data11 = cursor.fetchone()
    quantity2=data11[14]
    ppid=data11[0]
    mobile=data11[7]
    

    

    if request.method=='POST':
        maxid=request.form['maxid']
        payment=request.form['payment']
        
        cursor = mydb.cursor()
        cursor.execute("update book set payment=%s where id=%s",(payment, maxid))
        mydb.commit()
        msg="success"

        quan1=int(quantity1)
        quan2=int(quantity2)
        av_qty=quan2-quan1

        cursor = mydb.cursor()
        cursor.execute("update post set quantity=%s where id=%s",(av_qty, pid))
        mydb.commit()

        if av_qty < 10:
            
            
            st = "1"                
            mycursor.execute('SELECT * FROM post WHERE id=%s && quantity<10',(ppid,))
            dd = mycursor.fetchone()
            mess="Product:"+dd[2]+", is Low Quantity "+str(dd[14])+" Please check! "
        else:
            st = "0"

        
    else:
        msg="fail"

    return render_template('payment.html', maxid=maxid, msg=msg, total=total, st=st, mess=mess, mobile=mobile, name=name)




@app.route('/user_req', methods=['GET', 'POST'])
def user_req():
    if 'username' not in session or session.get('user_type') != 'farmer':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login'))

    
    username=session.get('username')

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM request where far_username = %s",(username,))
    data3 = cursor.fetchall()
    cursor.close()

    act=request.args.get("act")

    if act=="ok":
        aid=request.args.get("aid")
        cursor = mydb.cursor()
        cursor.execute("update request set action=1 where id=%s",(aid,))
        mydb.commit()
        print("successfully accepted")
        
    if act=="no":
        aid=request.args.get("aid")
        cursor = mydb.cursor()
        cursor.execute("update request set action=2 where id=%s",(aid,))
        mydb.commit()
        print("your account will be rejected")

    if request.method=='POST':
        aid=request.form['aid']
        date=request.form['date']
        time=request.form['time']
        cursor = mydb.cursor()
        cursor.execute("update request set date=%s, time=%s where id=%s",(date, time, aid))
        mydb.commit()

    return render_template('user_req.html', request=data3)


@app.route('/user_book', methods=['GET', 'POST'])
def user_book():
    if 'username' not in session or session.get('user_type') != 'farmer':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login'))

    
    username=session.get('username')

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM book where far_username = %s",(username,))
    data3 = cursor.fetchall()
    cursor.close()

    

    if request.method=='POST':
        aid=request.form['aid']
        order_status=request.form['order_status']
        cursor = mydb.cursor()
        cursor.execute("update book set status=%s where id=%s",(order_status, aid))
        mydb.commit()

    return render_template('user_book.html', book=data3)


@app.route('/view_book', methods=['GET', 'POST'])
def view_book():
    if 'username' not in session or session.get('user_type') != 'user':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login1'))

    
    username=session.get('username')

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM book where username = %s",(username,))
    data3 = cursor.fetchall()
    cursor.close()

    return render_template('view_book.html', book=data3)


@app.route('/view_req', methods=['GET', 'POST'])
def view_req():
    if 'username' not in session or session.get('user_type') != 'user':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login1'))

    
    username=session.get('username')

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM request where username = %s",(username,))
    data3 = cursor.fetchall()
    cursor.close()

    

    return render_template('view_req.html', request=data3)



@app.route('/my_product', methods=['GET', 'POST'])
def my_product():
    if 'username' not in session or session.get('user_type') != 'farmer':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login'))

    
    username=session.get('username')

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM post where username = %s",(username,))
    data3 = cursor.fetchall()
    cursor.close()

    

    return render_template('my_product.html', post=data3)



@app.route('/report', methods=['GET', 'POST'])
def report():

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM book")
    data3 = cursor.fetchall()
    cursor.close()

    

    return render_template('report.html', book=data3)



@app.route('/req', methods=['GET', 'POST'])
def req():

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM farmer")
    data3 = cursor.fetchall()
    cursor.close()
    act=request.args.get("act")


    if act=="ok":
        aid=request.args.get("aid")
        cursor = mydb.cursor()
        cursor.execute("update farmer set action=1 where id=%s",(aid,))
        mydb.commit()
        print("successfully accepted")
        
    if act=="no":
        aid=request.args.get("aid")
        cursor = mydb.cursor()
        cursor.execute("update farmer set action=2 where id=%s",(aid,))
        mydb.commit()
        print("your account will be rejected")

    

    return render_template('req.html', farmer=data3)



####################################################################################################3


@app.route("/call", methods=["GET", "POST"])
def call():

    aid=request.args.get("aid")
    if request.method == "POST":
        room_id = request.form['room_id']
        cursor = mydb.cursor()
        cursor.execute("update request set link=%s where id=%s",(room_id, aid))
        mydb.commit()
        
        return redirect(url_for("entry_checkpoint", room_id=room_id, aid=aid))

    return render_template("call.html")

@app.route("/room/<string:room_id>/")
def enter_room(room_id):
    act=request.args.get("act")
    
    
    if room_id not in session:
        return redirect(url_for("entry_checkpoint", room_id=room_id))
    
    return render_template("chatroom.html", room_id=room_id, display_name=session[room_id]["name"], mute_audio=session[room_id]["mute_audio"], mute_video=session[room_id]["mute_video"])

@app.route("/room/<string:room_id>/checkpoint/", methods=["GET", "POST"])
def entry_checkpoint(room_id):
    

    username=""
    
    if request.method == "POST":
        mute_audio = request.form['mute_audio']
        mute_video = request.form['mute_video']
        session[room_id] = {"name": username, "mute_audio":mute_audio, "mute_video":mute_video}
        return redirect(url_for("enter_room", room_id=room_id))

    return render_template("chatroom_checkpoint.html", room_id=room_id)

@socketio.on("connect")
def on_connect():
    sid = request.sid
    print("New socket connected ", sid)
    

@socketio.on("join-room")
def on_join_room(data):
    sid = request.sid
    room_id = data["room_id"]
    display_name = session[room_id]["name"]
    
    # register sid to the room
    join_room(room_id)
    _room_of_sid[sid] = room_id
    _name_of_sid[sid] = display_name
    
    # broadcast to others in the room
    print("[{}] New member joined: {}<{}>".format(room_id, display_name, sid))
    emit("user-connect", {"sid": sid, "name": display_name}, broadcast=True, include_self=False, room=room_id)
    
    # add to user list maintained on server
    if room_id not in _users_in_room:
        _users_in_room[room_id] = [sid]
        emit("user-list", {"my_id": sid}) # send own id only
    else:
        usrlist = {u_id:_name_of_sid[u_id] for u_id in _users_in_room[room_id]}
        emit("user-list", {"list": usrlist, "my_id": sid}) # send list of existing users to the new member
        _users_in_room[room_id].append(sid) # add new member to user list maintained on server

    print("\nusers: ", _users_in_room, "\n")


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    room_id = _room_of_sid[sid]
    display_name = _name_of_sid[sid]

    print("[{}] Member left: {}<{}>".format(room_id, display_name, sid))
    emit("user-disconnect", {"sid": sid}, broadcast=True, include_self=False, room=room_id)

    _users_in_room[room_id].remove(sid)
    if len(_users_in_room[room_id]) == 0:
        _users_in_room.pop(room_id)

    _room_of_sid.pop(sid)
    _name_of_sid.pop(sid)

    print("\nusers: ", _users_in_room, "\n")


@socketio.on("data")
def on_data(data):
    sender_sid = data['sender_id']
    target_sid = data['target_id']
    if sender_sid != request.sid:
        print("[Not supposed to happen!] request.sid and sender_id don't match!!!")

    if data["type"] != "new-ice-candidate":
        print('{} message from {} to {}'.format(data["type"], sender_sid, target_sid))
    socketio.emit('data', data, room=target_sid)





#FORUM########################################################################################3


@app.route('/ques',methods=['POST','GET'])
def ques():
    if 'username' not in session or session.get('user_type') != 'farmer':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login'))

    
    username=session.get('username')

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM questions where username = %s",(username,))
    data3 = cursor.fetchall()
    cursor.close()
    
    msg=""
    if request.method=='POST':
        question=request.form['question']
        
        now = datetime.datetime.now()
        reg_date=now.strftime("%Y-%m-%d")
        
        mycursor = mydb.cursor()
        
        mycursor.execute("SELECT max(id)+1 FROM questions")
        maxid = mycursor.fetchone()[0]
        if maxid is None:
            maxid=1
        sql = "INSERT INTO questions(id, question, reg_date, username) VALUES (%s, %s, %s, %s)"
        val = (maxid, question, reg_date, username)
        mycursor.execute(sql, val)
        mydb.commit()

        msg="success"


    
  
    return render_template('ques.html', msg=msg, questions=data3)



@app.route('/sugg',methods=['POST','GET'])
def sugg():
    if 'username' not in session or session.get('user_type') != 'farmer':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login'))

    
    username=session.get('username')

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM questions")
    data3 = cursor.fetchall()
    cursor.close()
    
  
    return render_template('sugg.html', questions=data3)


@app.route('/write',methods=['POST','GET'])
def write():
    if 'username' not in session or session.get('user_type') != 'farmer':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login'))

    
    username=session.get('username')

    qid=request.args.get("qid")
    
    msg=""
    if request.method=='POST':
        sugges=request.form['sugges']
        
        now = datetime.datetime.now()
        reg_date=now.strftime("%Y-%m-%d")
        
        mycursor = mydb.cursor()
        
        mycursor.execute("SELECT max(id)+1 FROM suggestion")
        maxid = mycursor.fetchone()[0]
        if maxid is None:
            maxid=1
        sql = "INSERT INTO suggestion(id, qid, reg_date, sugges, username) VALUES (%s, %s, %s, %s, %s)"
        val = (maxid, qid, reg_date, sugges, username)
        mycursor.execute(sql, val)
        mydb.commit()

        msg="success"
    
  
    return render_template('write.html', msg=msg)


@app.route('/view_sugg',methods=['POST','GET'])
def view_sugg():
    if 'username' not in session or session.get('user_type') != 'farmer':
        print("Please log in as a admin to access the page.", 'danger')
        return redirect(url_for('login'))

    
    sid=request.args.get('sid')

    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM suggestion where id=%s",(sid, ))
    data3 = cursor.fetchall()
    cursor.close()
    
  
    return render_template('view_sugg.html', suggestion=data3)









@app.route('/logout')
def logout():
    
    session.clear()
    print("Logged out successfully", 'success')
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)


