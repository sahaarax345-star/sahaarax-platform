from flask import Flask, render_template, request, redirect, url_for, flash,session
from werkzeug.utils import secure_filename
import os
import re
import uuid
import projectrec
import yagmail
import random, string
import google.generativeai as genai
from flask import jsonify
from datetime import datetime
import uuid
# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta
import uuid, json
from flask import request, render_template, redirect, url_for, flash
from google.generativeai import configure, GenerativeModel
# Direct API key set karo
configure(api_key="AIzaSyB3VgAik36l1ZjSATlYY_p3jUkpAq8_Po4")

#  Model select
model = GenerativeModel("gemini-1.5-flash")
app = Flask(__name__)
app.secret_key = "007219"  # CHANGE THIS
# Firebase setup
cred = credentials.Certificate(r"C:\Users\hp\Desktop\project\database.json")  # Put your Firebase service account key file here
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://sahara-app-d97e0-default-rtdb.firebaseio.com/',
    'storageBucket': 'your-bucket-name.appspot.com'
})

app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Home Route
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/con')
def con():
    return render_template('con.html')

@app.route('/rom')
def rom():
    return render_template('rom.html')


@app.route('/user_signup')
def user():
    return render_template('signup.html')

@app.route('/mod')
def mod():
    return render_template('mod.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        def g(name, default=""):
            return request.form.get(name, default).strip()

        # fields
        name = g('name')
        father_name = g('father_name')
        marital_status = g('marital_status')
        husband_name = g('husband_name') if marital_status == 'yes' else ''
        children = g('children')
        children_count = g('children_count') if children == 'yes' else ''
        gender = g('gender')
        age = g('age')
        cnic = g('cnic')
        current_location = g('current_location')
        description = g('description')
        contact_number = g('contact_number')
        email = g('email')
        username = g('username')
        address = g('address')
        counseling = request.form.getlist('counseling')

        # 🚨 Validations

        if not re.fullmatch(r"[A-Za-z\s]+", name):
            flash("Name must contain only alphabets.")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"[A-Za-z\s]+", father_name):
            flash("Father Name must contain only alphabets.")
            return redirect(url_for('signup'))

        if not age.isdigit() or int(age) < 10:
            flash("Age must be a number and at least 10.")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"\d{13}", cnic or ""):
            flash("CNIC must be exactly 13 digits.")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email or ""):
            flash("Invalid email format.")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"\d{11}", contact_number or ""):
            flash("Contact number must be exactly 11 digits.")
            return redirect(url_for('signup'))

        # 🚨 Duplicate check in Firebase
        ref = db.reference('users')
        users_data = ref.get() or {}

        for uid, user in users_data.items():
            if user.get('cnic') == cnic:
                flash("CNIC already registered!")
                return redirect(url_for('signup'))
            if user.get('email') == email:
                flash("Email already registered!")
                return redirect(url_for('signup'))
            if user.get('contact_number') == contact_number:
                flash("Phonenumber already registered!")
                return redirect(url_for('signup'))

        # file uploads
        profile_img = request.files.get('profile_image')
        legal_docs = request.files.get('legal_docs')
        uid = str(uuid.uuid4())
        profile_img_path = ""
        legal_doc_path = ""

        if profile_img and profile_img.filename:
            safe_name = secure_filename(profile_img.filename)
            profile_img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uid}_profile_{safe_name}")
            profile_img.save(profile_img_path)
        else:
            flash("Profile image is required.")
            return redirect(url_for('signup'))

        if legal_docs and legal_docs.filename:
            safe_name = secure_filename(legal_docs.filename)
            legal_doc_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uid}_legal_{safe_name}")
            legal_docs.save(legal_doc_path)

        # categories
        categories = request.form.getlist('categories')

        # children details
        children_details = []
        if children == 'yes':
            names = request.form.getlist('child_name[]')
            relations = request.form.getlist('child_relation[]')
            ages = request.form.getlist('child_age[]')
            for nm, rel, ag in zip(names, relations, ages):
                if nm.strip():
                    if not ag.isdigit() or int(ag) >= 8:
                        flash("Each child's age must be less than 8.")
                        return redirect(url_for('signup'))
                    children_details.append({
                        'name': nm,
                        'relation': rel,
                        'age': ag
                    })

        # push to firebase
        ref.child(uid).set({
            'name': name,
            'father_name': father_name,
            'marital_status': marital_status,
            'husband_name': husband_name,
            'legal_doc_path': legal_doc_path,
            'children': children,
            'children_count': children_count,
            'children_details': children_details,
            'gender': gender,
            'age': age,
            'cnic': cnic,
            'current_location': current_location,
            'description': description,
            'categories': categories,
            'counseling': counseling,
            'contact_number': contact_number,
            'email': email,
            'username': username,
            'address': address,
            'profile_image_path': profile_img_path,
            'status': 'Unapproved'
        })

        flash("Signup successful! Your data is pending approval.")
        return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        ref = db.reference("admin")
        admin_data = ref.get()
        if admin_data:
            # Single admin check
            if email == admin_data.get("email"):
                if password == admin_data.get("password"):
                    session["admin"] = email
                    flash("Login successful!", "success")
                    return redirect(url_for("dashboard"))
                else:
                    flash("Invalid password!", "error")
                    return redirect(url_for("admin_login"))
            else:
                flash("Admin email not found!", "error")
                return redirect(url_for("admin_login"))
        else:
            flash("No admin data found in Firebase!", "error")
            return redirect(url_for("admin_login"))

    return render_template("admin_login.html")



# Email Setup
yag = yagmail.SMTP("saharax191@gmail.com", "ctravpkafztcmjiu")

def generate_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route("/view_users")
def view_users():
    # Get filters from query params
    filter_status = request.args.get("status", "").strip()
    filter_category = request.args.get("category", "").strip()
    filter_children = request.args.get("children", "").strip()
    search_username = request.args.get("username", "").strip().lower()
    search_email = request.args.get("email", "").strip().lower()

    ref = db.reference("users")
    users = ref.get() or {}

    approved = sum(1 for u in users.values() if u.get("status") == "Approved")
    rejected = sum(1 for u in users.values() if u.get("status") == "Rejected")
    unapproved = sum(1 for u in users.values() if u.get("status") == "Unapproved")

    pending_users = {uid: u for uid, u in users.items() if u.get("status") == "Unapproved"}

    filtered_users = {}

    for user_id, user in users.items():
        match = True

        #  Status filter
        if filter_status and user.get("status", "").lower() != filter_status.lower():
            match = False

        # Category filter
        if filter_category and filter_category != "All":
            cats = user.get("categories", [])
            if isinstance(cats, str):  # convert to list if single string
                cats = [cats]
            cats = [c.lower() for c in cats]
            if filter_category.lower() not in cats:
                match = False

        #  Children filter
        if filter_children == "with" and user.get("children", "").lower() != "yes":
            match = False
        if filter_children == "without" and user.get("children", "").lower() != "no":
            match = False

        #  Username search
        if search_username and search_username not in user.get("username", "").lower():
            match = False

        #  Email search
        if search_email and search_email not in user.get("email", "").lower():
            match = False

        if match:
            filtered_users[user_id] = user

    return render_template(
        "view_users.html",
        users=filtered_users,
        filter_status=filter_status,
        filter_category=filter_category,
        approved=approved,
        rejected=rejected,
        unapproved=unapproved,
        pending_users=pending_users,
        filter_children=filter_children
    )



# ---------------- APPROVE USER ----------------
@app.route("/approve_user/<user_id>")
def approve_user(user_id):
    ref = db.reference("users").child(user_id)
    user = ref.get()
    if not user:
        flash("User not found", "error")
        return redirect(url_for("view_users"))

    password = generate_password()
    ref.update({"status": "Approved", "password": password})

    subject = "SahaaraX Account Approved"
    body = f"""
    Dear {user['name']},

    Your account has been approved 

    Login credentials:
    Email: {user['email']}
    Password: {password}

    Regards,
    SahaaraX Team
    """
    yag.send(user["email"], subject, body)
    flash(f"User {user['name']} approved!", "success")
    return redirect(url_for("view_users"))


# ---------------- REJECT USER ----------------
@app.route("/reject_user/<user_id>")
def reject_user(user_id):
    ref = db.reference("users").child(user_id)
    user = ref.get()
    if not user:
        flash("User not found", "error")
        return redirect(url_for("view_users"))

    ref.update({"status": "Rejected"})

    subject = "SahaaraX Account Rejected"
    body = f"""
    Dear {user['name']},

    Unfortunately, your account has been rejected ❌
    Please contact our support team for more details.

    Regards,
    SahaaraX Team
    """
    yag.send(user["email"], subject, body)
    flash(f"User {user['name']} rejected!", "danger")
    return redirect(url_for("view_users"))


@app.route('/delete_user/<user_id>')
def delete_user(user_id):
    ref = db.reference('users').child(user_id)
    user = ref.get()
    if not user:
        flash("User not found", "error")
        return redirect(url_for('view_users'))

    ref.delete()
    flash(f"User {user['name']} has been permanently deleted.", "success")
    return redirect(url_for('view_users'))




@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("admin_login"))

    ref = db.reference("users")
    users = ref.get() or {}



    ref_room = db.reference("rooms")
    rooms = ref_room.get() or {}

    total_rooms = len(rooms)

    # Total beds (sum of bed_count from each room)
    total_beds = sum(int(room.get("bed_count", 0)) for room in rooms.values())
    print(total_beds)

    approved = sum(1 for u in users.values() if u.get("status") == "Approved")
    rejected = sum(1 for u in users.values() if u.get("status") == "Rejected")
    unapproved = sum(1 for u in users.values() if u.get("status") == "Unapproved")
    # ✅ Only approved users
    approved_users = {
        uid: u for uid, u in users.items()
        if u.get("status", "").lower() == "approved"
    }
    #  Collect unapproved users
    pending_users = {uid: u for uid, u in users.items() if u.get("status") == "Unapproved"}
    #  Stats counters
    stats = {
        "Domestic Violence": 0,
        "Sexual Abuse Support": 0,
        "Psychological Support": 0,
        "Self Awareness": 0,
        "Health Awareness": 0,
    }

    for uid, user in approved_users.items():
        counseling = user.get("counseling", [])
        if isinstance(counseling, str):
            counseling = [counseling]

        # Count for stats
        for c in counseling:
            if c in stats:
                stats[c] += 1
    return render_template(
        "dashboard.html",
        admin_email=session["admin"],
        approved=approved,
        rejected=rejected,
        unapproved=unapproved,
        pending_users=pending_users,
        total_beds=total_beds,
        stats=stats,
        total_rooms=total_rooms
    )


# Folder for room images
ROOM_UPLOAD_FOLDER = os.path.join("static", "room_photos")
os.makedirs(ROOM_UPLOAD_FOLDER, exist_ok=True)


@app.route("/add_room", methods=["GET", "POST"])
def add_room():
    if request.method == "POST":
        floor = request.form.get("floor").strip()
        room_number = request.form.get("room_number").strip()
        bed_count = int(request.form.get("bed_count"))

        ref = db.reference("rooms")
        rooms = ref.get() or {}

        #  Only check for duplicate Floor + Room number combo
        for rid, room in rooms.items():
            if str(room.get("floor")) == floor and str(room.get("room_number")) == room_number:
                flash("⚠️ This room already exists on the same floor!", "danger")
                return redirect(url_for("add_room"))

        #  Handle Images (3 image inputs)
        images = [
            request.files.get("image1"),
            request.files.get("image2"),
            request.files.get("image3")
        ]
        img_paths = []

        for img in images:
            if img and img.filename:
                filename = secure_filename(f"{uuid.uuid4()}_{img.filename}")
                save_path = os.path.join("static/room_photos", filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                img.save(save_path)
                img_paths.append(f"room_photos/{filename}")

        #  Save in Firebase
        room_id = str(uuid.uuid4())
        ref.child(room_id).set({
            "floor": floor,
            "room_number": room_number,
            "bed_count": bed_count,
            "available_beds": bed_count,
            "images": img_paths
        })

        flash(" Room added successfully!", "success")
        return redirect(url_for("view_rooms"))

    return render_template("add_room.html")




@app.route("/view_rooms", methods=["GET"])
def view_rooms():
    ref = db.reference("rooms")
    rooms = ref.get() or {}

    #  Floor filter from query param
    selected_floor = request.args.get("floor", "").strip()

    filtered_rooms = {}
    for rid, room in rooms.items():
        if selected_floor and selected_floor != "All":
            if str(room.get("floor")) == selected_floor:
                filtered_rooms[rid] = room
        else:
            filtered_rooms[rid] = room

    total_rooms = len(filtered_rooms)
    total_available_beds = sum(int(room.get("available_beds", 0)) for room in filtered_rooms.values())

    # Get unique floors for dropdown
    unique_floors = sorted({str(room.get("floor")) for room in rooms.values() if room.get("floor")})

    return render_template(
        "view_rooms.html",
        rooms=filtered_rooms,
        total_rooms=total_rooms,
        total_available_beds=total_available_beds,
        selected_floor=selected_floor,
        unique_floors=unique_floors
    )

@app.route("/edit_room/<room_id>", methods=["GET", "POST"])
def edit_room(room_id):
    ref = db.reference("rooms").child(room_id)
    room = ref.get()

    if request.method == "POST":
        floor = request.form.get("floor")
        room_number = request.form.get("room_number")
        bed_count = int(request.form.get("bed_count"))

        # Existing images
        updated_images = room.get("images", [])

        # Handle new uploads (overwrite if new image provided)
        for i, field in enumerate(["image1", "image2", "image3"]):
            img = request.files.get(field)
            if img and img.filename:
                filename = secure_filename(f"{uuid.uuid4()}_{img.filename}")
                save_path = os.path.join("static/room_photos", filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                img.save(save_path)

                if len(updated_images) > i:
                    updated_images[i] = f"room_photos/{filename}"  # replace
                else:
                    updated_images.append(f"room_photos/{filename}")  # add new

        # Save updated data
        ref.update({
            "floor": floor,
            "room_number": room_number,
            "bed_count": bed_count,
            "available_beds": room.get("available_beds", bed_count),
            "images": updated_images[:3]  # ensure max 3
        })

        flash("Room updated successfully!", "success")
        return redirect(url_for("view_rooms"))

    return render_template("edit_room.html", room=room)


@app.route("/delete_room/<room_id>", methods=["GET", "POST"])
def delete_room(room_id):
    ref = db.reference("rooms").child(room_id)
    room = ref.get()

    if not room:
        flash("Room not found!", "error")
        return redirect(url_for("view_rooms"))

    #  Check if room is assigned to any user
    users_ref = db.reference("users")
    users = users_ref.get() or {}

    assigned_user = None
    for uid, user in users.items():
        if user.get("assigned_room") == room_id:  # check by room_id
            assigned_user = {
                "id": uid,
                "name": user.get("name"),
                "email": user.get("email"),
                "profile_image": user.get("profile_image_path"),
                "shelter_start_date": user.get("shelter_start_date"),
                "shelter_expiry_date": user.get("shelter_expiry_date"),
                "shelter_status": user.get("shelter_status")
            }
            break

    if assigned_user:
        # 🚨 Do not delete, show popup instead with shelter details
        return render_template("room_assigned_warning.html",
                               room=room,
                               user=assigned_user)

    #  If no user assigned → Delete room + images
    for img in room.get("images", []):
        try:
            os.remove(os.path.join("static", img))  # delete from static
        except:
            pass

    ref.delete()
    flash("Room deleted successfully!", "success")
    return redirect(url_for("view_rooms"))



@app.route("/shelter", methods=["GET", "POST"])
def shelter():
    selected_category = request.args.get("category", "").strip()

    ref_users = db.reference("users")
    users = ref_users.get() or {}

    #  Approved users only
    approved_users = {
        uid: u for uid, u in users.items() if u.get("status", "").lower() == "approved"
    }

    filtered_users = {}
    if selected_category and selected_category != "All":
        for uid, u in approved_users.items():
            cats = u.get("categories", [])
            if isinstance(cats, str):
                cats = [cats]
            cats = [c.lower().strip() for c in cats]
            if selected_category.lower() in cats:
                filtered_users[uid] = u
    else:
        filtered_users = approved_users

    #  Handle Shelter Allotment
    if request.method == "POST":
        user_id = request.form.get("user_id")
        room_id = request.form.get("room_id")

        if not user_id or not room_id:
            flash("Invalid request! Please select a user and room.", "error")
            return redirect(url_for("shelter", category=selected_category))

        # Fetch user
        user = ref_users.child(user_id).get()
        if not user:
            flash("User not found!", "error")
            return redirect(url_for("shelter", category=selected_category))

        # Fetch room
        ref_rooms = db.reference("rooms")
        room = ref_rooms.child(room_id).get()
        if not room:
            flash("Room not found!", "error")
            return redirect(url_for("shelter", category=selected_category))

        #  Check available beds
        bed_count = int(room.get("bed_count", 0))
        if bed_count <= 0:
            flash(f"Room {room.get('room_number')} is already FULL!", "danger")
            return redirect(url_for("shelter", category=selected_category))

        #  Allot user under Shelter child
        ref_shelter = db.reference("Shelter").child(room_id).child(user_id)
        ref_shelter.set(user)

        #  Reduce bed count by 1
        new_beds = bed_count - 1
        ref_rooms.child(room_id).update({"bed_count": new_beds})

        flash(f"User {user['name']} allotted to Room {room.get('room_number')} ✅ (Remaining Beds: {new_beds})", "success")
        return redirect(url_for("shelter", category=selected_category))

    #  Get all rooms for dropdown
    ref_rooms = db.reference("rooms")
    rooms = ref_rooms.get() or {}

    return render_template(
        "shelter.html",
        selected_category=selected_category,
        users=filtered_users,
        rooms=rooms
    )

@app.route("/assign_shelter/<user_id>", methods=["GET", "POST"])
def assign_shelter(user_id):
    ref_users = db.reference("users").child(user_id)
    user = ref_users.get()

    if not user:
        flash("User not found", "error")
        return redirect(url_for("shelter"))

    # Rooms reference
    ref_rooms = db.reference("rooms")
    rooms = ref_rooms.get() or {}

    #  Form Submit
    if request.method == "POST":
        room_id = request.form.get("room_id")
        start_date = request.form.get("start_date")
        expiry_date = request.form.get("expiry_date")
        notify = request.form.get("notify")  # hidden field from button

        if notify == "yes":
            # Send notification email
            subject = "SahaaraX - Shelter Request Pending"
            body = f"""
            Dear {user['name']},

            Unfortunately, there are no beds available in the selected shelter at the moment.
            Our team will notify you as soon as a bed becomes available.

            Regards,
            SahaaraX Team
            """
            yag.send(user["email"], subject, body)
            flash("User notified via email about unavailability of beds.", "info")
            return redirect(url_for("shelter"))

        if not room_id or not start_date or not expiry_date:
            flash("All fields are required", "error")
            return redirect(url_for("assign_shelter", user_id=user_id))

        # Check if already assigned
        if user.get("assigned_room"):
            flash("This user already has a room assigned!", "warning")
            return redirect(url_for("shelter"))

        room = rooms.get(room_id)
        if not room:
            flash("Room not found!", "error")
            return redirect(url_for("assign_shelter", user_id=user_id))

        #  Check bed availability
        if int(room.get("available_beds", 0)) <= 0:
            flash("⚠️ No beds available! You can notify the user.", "warning")
            return render_template("assign_shelter.html", user=user, user_id=user_id, rooms=rooms, no_beds=True)

        # Assign room to user
        ref_users.update({
            "assigned_room": room_id,
            "shelter_start_date": start_date,
            "shelter_expiry_date": expiry_date,
            "shelter_status": "active"
        })

        # Update bed count in room
        new_bed_count = int(room["available_beds"]) - 1
        ref_rooms.child(room_id).update({"available_beds": new_bed_count})

        flash(f"Shelter assigned successfully! Room: {room_id}", "success")
        return redirect(url_for("shelter"))

    return render_template("assign_shelter.html", user=user, user_id=user_id, rooms=rooms, no_beds=False)

@app.route("/check_shelter_expiry")
def check_shelter_expiry():
    ref_users = db.reference("users")
    users = ref_users.get() or {}

    now = datetime.now()

    for uid, user in users.items():
        expiry_str = user.get("shelter_expiry_date")
        if user.get("assigned_room") and expiry_str:
            expiry_date = None

            #  Multiple formats handle karna
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    expiry_date = datetime.strptime(expiry_str, fmt)
                    break
                except ValueError:
                    continue

            if not expiry_date:
                continue  # Agar format hi galat hai, skip

            days_left = (expiry_date - now).days

            if days_left <= 2 and user.get("shelter_status") == "Active":
                subject = "⚠️ Shelter Expiry Alert"
                body = f"""
                Dear Admin,

                User {user['name']} ({user['email']})'s shelter is expiring soon.

                Room: {user['assigned_room']}
                Expiry Date: {expiry_str}

                Please take action.

                Regards,
                SahaaraX System
                """
                yag.send("admin_email@gmail.com", subject, body)
                flash(f"Expiry alert sent for {user['name']}", "info")

    return "Checked expiry and sent alerts."


@app.route("/check_expired_shelters")
def check_expired_shelters():
    ref_users = db.reference("users")
    users = ref_users.get() or {}

    ref_rooms = db.reference("rooms")
    ref_expired = db.reference("expired_shelters")

    today = datetime.today().date()

    for uid, user in users.items():
        expiry_date = user.get("shelter_expiry_date")
        room_id = user.get("assigned_room")
        status = user.get("shelter_status", "")

        if expiry_date and room_id and status == "active":
            try:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            except ValueError:
                continue  # skip invalid dates

            #  Check if expired
            if today >= expiry:
                # Move record to expired_shelters
                ref_expired.push({
                    "user_id": uid,
                    "room_id": room_id,
                    "start_date": user.get("shelter_start_date"),
                    "expiry_date": expiry_date
                })

                # Free the bed in that room
                room = ref_rooms.child(room_id).get()
                if room:
                    new_beds = int(room.get("bed_count", 0)) + 1
                    ref_rooms.child(room_id).update({"bed_count": new_beds})

                # Update user status
                ref_users.child(uid).update({
                    "shelter_status": "expired",
                    "assigned_room": None
                })

    flash("Expired shelters checked and updated.", "info")
    return redirect(url_for("shelter"))

@app.route("/assigned_shelters")
def assigned_shelters():
    # Get users + rooms
    users_ref = db.reference("users")
    rooms_ref = db.reference("rooms")

    users = users_ref.get() or {}
    rooms = rooms_ref.get() or {}

    assigned_users = {}

    for uid, user in users.items():
        room_id = user.get("assigned_room")
        if room_id:  # only users with assigned rooms
            room = rooms.get(room_id)
            if room:
                user["room_details"] = room  # attach room info
                assigned_users[uid] = user

    return render_template("assigned_shelters.html", users=assigned_users)




@app.route("/release_shelter/<user_id>")
def release_shelter(user_id):
    ref_users = db.reference("users").child(user_id)
    user = ref_users.get()

    if not user:
        flash("User not found!", "error")
        return redirect(url_for("assigned_shelters"))

    room_id = user.get("assigned_room")
    if not room_id:
        flash("This user does not have a room assigned!", "warning")
        return redirect(url_for("assigned_shelters"))

    # Room reference
    ref_rooms = db.reference("rooms").child(room_id)
    room = ref_rooms.get()

    if room:
        # Increase available beds back
        new_beds = int(room.get("available_beds", 0)) + 1
        ref_rooms.update({"available_beds": new_beds})

    # Reset user shelter details
    ref_users.update({
        "assigned_room": None,
        "shelter_start_date": None,
        "shelter_expiry_date": None,
        "shelter_status": "released"
    })

    # Send email
    subject = "SahaaraX - Thank You"
    body = f"""
    Dear {user['name']},

    Thank you for staying with SahaaraX Shelter. 
    We are glad to have supported you during this period. 

    Your shelter stay has now ended. 
    Wishing you the very best ahead!

    Regards,
    SahaaraX Team
    """
    try:
        yag.send(user["email"], subject, body)
    except Exception as e:
        print("Email error:", e)

    flash(f"Shelter released for {user['name']}. Room bed updated.", "success")
    return redirect(url_for("assigned_shelters"))




@app.route("/counseling", methods=["GET"])
def counseling():
    filter_counseling = request.args.get("counseling", "").strip()

    ref = db.reference("users")
    users = ref.get() or {}

    #  Only approved users
    approved_users = {
        uid: u for uid, u in users.items()
        if u.get("status", "").lower() == "approved"
    }

    # Get counselor assignments
    assignment_ref = db.reference("assign_conseler")
    assignments = assignment_ref.get() or {}
    counselor_map = {}
    for aid, data in assignments.items():
        uid = data.get("user_id")
        if uid:
            counselor_map[uid] = {
                "name": data.get("counselor_name"),
                "email": data.get("counselor_email"),
                "category": data.get("counseling"),
                "timestamp": data.get("timestamp")
            }

    filtered_users = {}
    stats = {
        "Domestic Violence": 0,
        "Sexual Abuse Support": 0,
        "Psychological Support": 0,
        "Self Awareness": 0,
        "Health Awareness": 0,
    }

    for uid, user in approved_users.items():
        counseling = user.get("counseling", [])
        if isinstance(counseling, str):
            counseling = [counseling]

        # Stats
        for c in counseling:
            if c in stats:
                stats[c] += 1

        # Filter
        if filter_counseling and filter_counseling != "All":
            if filter_counseling in counseling:
                pass
            else:
                continue

        # Add assigned counselor info if exists
        if uid in counselor_map:
            user["assigned_counselor"] = counselor_map[uid]
        filtered_users[uid] = user

    return render_template(
        "counseling.html",
        users=filtered_users,
        filter_counseling=filter_counseling,
        stats=stats
    )


#  Get Counselors Modal Data (AJAX)
@app.route("/get_counselors/<user_id>")
def get_counselors(user_id):
    user = db.reference("users").child(user_id).get()
    if not user:
        return {"error": "User not found"}, 404

    category = user.get("counseling")
    if isinstance(category, list):
        category = category[0]

    counselors = {}
    ref = db.reference("conseling_signup")
    all_counselors = ref.get() or {}
    for cid, cons in all_counselors.items():
        if cons.get("counseling") == category:
            counselors[cid] = cons

    return {"counselors": counselors, "category": category}

#  Assign Counselor
@app.route("/assign_counselor", methods=["POST"])
def assign_counselor():
    user_id = request.form.get("user_id")
    counselor_id = request.form.get("counselor_id")

    user = db.reference("users").child(user_id).get()
    counselor = db.reference("conseling_signup").child(counselor_id).get()

    if not user or not counselor:
        flash("User or counselor not found!", "error")
        return redirect(url_for("counseling"))

    # Save assignment in DB
    assign_id = str(uuid.uuid4())
    db.reference("assign_conseler").child(assign_id).set({
        "user_id": user_id,
        "user_name": user["name"],
        "user_email": user["email"],
        "counselor_id": counselor_id,
        "counselor_name": counselor["name"],
        "counselor_email": counselor["email"],
        "counseling": counselor["counseling"],
        "timestamp": str(datetime.now())
    })

    # Send email
    yag.send(
        user["email"],
        "Counselor Assigned - SahaaraX",
        f"""
        Dear {user['name']},

        A counselor has been assigned to you for {counselor['counseling']}.

        Counselor: {counselor['name']}
        Email: {counselor['email']}

        Regards,
        SahaaraX Team
        """
    )

    flash("Counselor assigned and email sent successfully!", "success")
    return redirect(url_for("counseling"))

@app.route("/conseling_signup", methods=["GET", "POST"])
def conseling_signup():
    if request.method == "POST":
        def is_alpha(value):
            return re.fullmatch(r"[A-Za-z\s]+", value)

        def is_valid_email(value):
            return re.fullmatch(r"[^@]+@[^@]+\.[^@]+", value)

        def is_valid_phone(value):
            return re.fullmatch(r"\d{11}", value)

        # Get values
        name = request.form.get("name", "").strip()
        father_name = request.form.get("father_name", "").strip()
        email = request.form.get("email", "").strip()
        gender = request.form.get("gender", "")
        counseling = request.form.get("counseling", "")
        dob = request.form.get("dob", "")
        phone = request.form.get("phone", "")
        availability = request.form.get("availability", "")
        location = request.form.get("location", "")

        #  Validations
        if not is_alpha(name):
            flash("Name must contain only alphabets.", "danger")
            return redirect(url_for("conseling_signup"))

        if not is_alpha(father_name):
            flash("Father Name must contain only alphabets.", "danger")
            return redirect(url_for("conseling_signup"))

        if not is_valid_email(email):
            flash("Invalid email format.", "danger")
            return redirect(url_for("conseling_signup"))

        if not is_valid_phone(phone):
            flash("Phone number must be exactly 11 digits.", "danger")
            return redirect(url_for("conseling_signup"))

        if not dob:
            flash("Date of birth is required.", "danger")
            return redirect(url_for("conseling_signup"))

        try:
            datetime.strptime(dob, "%Y-%m-%d")
        except ValueError:
            flash("Date of birth format should be YYYY-MM-DD.", "danger")
            return redirect(url_for("conseling_signup"))

        #  Save profile image
        profile_img = request.files.get("profile_image")
        profile_img_path = ""
        if not profile_img or not profile_img.filename:
            flash("Profile image is required.", "danger")
            return redirect(url_for("conseling_signup"))

        if not profile_img.mimetype.startswith("image/"):
            flash("Only image files are allowed for profile image.", "danger")
            return redirect(url_for("conseling_signup"))

        filename = secure_filename(f"{uuid.uuid4()}_{profile_img.filename}")
        save_path = os.path.join("static/profile_photos", filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        profile_img.save(save_path)
        profile_img_path = f"profile_photos/{filename}"

        #  Save documents
        document = request.files.get("document")
        document_path = ""
        if document and document.filename:
            filename = secure_filename(f"{uuid.uuid4()}_{document.filename}")
            save_path = os.path.join("static/conseling_documents", filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            document.save(save_path)
            document_path = f"conseling_documents/{filename}"

        #  Generate random password
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        #  Save to Firebase
        uid = str(uuid.uuid4())
        db.reference("conseling_signup").child(uid).set({
            "name": name,
            "father_name": father_name,
            "email": email,
            "gender": gender,
            "counseling": counseling,
            "dob": dob,
            "phone": phone,
            "availability": availability,
            "location": location,
            "profile_image": profile_img_path,
            "document": document_path,
            "password": password
        })

        #  Send email
        subject = "SahaaraX Counseling Signup - Login Credentials"
        body = f"""
        Dear {name},

        Your counseling signup was successful 

        Login Credentials:
        Email: {email}
        Password: {password}

        Regards,  
        SahaaraX Team
        """
        yag.send(email, subject, body)

        flash("Counseling Signup Successful! Login details sent to email.", "success")
        return redirect(url_for("conseling_signup"))

    return render_template("conseling_signup.html")

# ---------------- Counseling Sign In ----------------
@app.route("/counseling_signin", methods=["GET", "POST"])
def counseling_signin():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash(" Please enter both email and password.", "danger")
            return redirect(url_for("counseling_signin"))

        ref = db.reference("conseling_signup")  #  database path
        users = ref.get() or {}

        for uid, user in users.items():
            db_email = str(user.get("email", "")).strip().lower()
            db_password = str(user.get("password", "")).strip()
            db_type = user.get("counseling", "").strip()  #  counseling type fetch

            #  email match case-insensitive
            if db_email == email.lower():
                if db_password == password:
                    session["counseling_user"] = uid
                    session["counseling_type"] = db_type  #  store type in session
                    flash(" Login successful!", "success")

                    # Redirect based on type
                    if db_type in ["Domestic Violence", "Sexual Abuse Support", "Psychological Support"]:
                        return redirect(url_for("counseling_signin"))
                    elif db_type in ["Self Awareness", "Health Awareness"]:
                        return redirect(url_for("awareness_dashboard"))
                    else:
                        flash("Invalid counseling type!", "danger")
                        return redirect(url_for("counseling_signin"))
                else:
                    flash(" Invalid password!", "danger")
                    return redirect(url_for("counseling_signin"))

        flash(" Email not found!", "danger")
        return redirect(url_for("counseling_signin"))

    return render_template("counseling_signin.html")

# Step 1: Forgot password (enter role & email)
@app.route("/counselor_forget", methods=["GET", "POST"])
def counselor_forget():
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not role or not email:
            flash(" Please select role and enter email.", "warning")
            return redirect(url_for("counselor_forget"))

        # Path check (Counseling vs Awareness)
        path = "conseling_signup" if role == "Counseling" else "awareness_signup"
        users = db.reference(path).get() or {}

        user_id, user_name = None, None
        for uid, user in users.items():
            db_email = str(user.get("email", "")).strip().lower()
            if db_email == email:
                user_id = uid
                user_name = user.get("name", "User")
                break

        if not user_id:
            flash(" Email not found!", "danger")
            return redirect(url_for("counselor_forget"))

        # Generate OTP
        otp = random.randint(100000, 999999)
        session["reset_user"] = {"id": user_id, "role": role, "email": email, "otp": str(otp)}

        # Send OTP email
        try:
            yag = yagmail.SMTP("saharax191@gmail.com", "ctravpkafztcmjiu")
            yag.send(
                to=email,
                subject="Password Reset Code - SahaaraX",
                contents=f"Hello {user_name},\n\nYour verification code is: {otp}\n\nTeam SahaaraX"
            )
            flash(" Verification code sent to your email.", "success")
            return redirect(url_for("counselor_verify"))
        except Exception as e:
            print("Email error:", e)
            flash(" Failed to send email. Try again later.", "danger")
            return redirect(url_for("counselor_forget"))

    return render_template("counselor_forget.html")


# Step 2: Verify OTP
@app.route("/counselor_verify", methods=["GET", "POST"])
def counselor_verify():
    reset_info = session.get("reset_user")
    if not reset_info:
        flash(" Session expired, please try again.", "warning")
        return redirect(url_for("counselor_forget"))

    if request.method == "POST":
        code = request.form.get("otp", "").strip()
        if code == reset_info["otp"]:
            return redirect(url_for("counselor_reset"))
        else:
            flash(" Invalid verification code!", "danger")
            return redirect(url_for("counselor_verify"))

    return render_template("counselor_verify.html", email=reset_info["email"])


# Step 3: Reset Password
@app.route("/counselor_reset", methods=["GET", "POST"])
def counselor_reset():
    reset_info = session.get("reset_user")
    if not reset_info:
        flash(" Session expired, please try again.", "warning")
        return redirect(url_for("counselor_forget"))

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        if not password or not confirm:
            flash(" Please enter both fields.", "warning")
            return redirect(url_for("counselor_reset"))

        if password != confirm:
            flash(" Passwords do not match!", "danger")
            return redirect(url_for("counselor_reset"))

        path = "conseling_signup" if reset_info["role"] == "Counseling" else "awareness_signup"
        db.reference(path).child(reset_info["id"]).update({"password": password})

        session.pop("reset_user", None)
        flash(" Password reset successful! Please login.", "success")
        return redirect(url_for("counseling_signin"))

    return render_template("counselor_reset.html")



# ---------------- Counseling Dashboard ----------------
@app.route("/counseling_dashboard")
def counseling_dashboard():
    if "counseling_user" not in session:
        flash(" Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["counseling_user"]
    counselor = db.reference("conseling_signup").child(counselor_id).get()

    if not counselor:
        flash("Counselor not found in database!", "danger")
        return redirect(url_for("counseling_signin"))

    # Assigned users
    assigned_ref = db.reference("assign_conseler")
    assignments = assigned_ref.get() or {}

    assigned_users = []
    for aid, assign in assignments.items():
        if assign.get("counselor_id") == counselor_id:
            assign["user_id"] = assign.get("user_id")
            assigned_users.append(assign)

    return render_template("counseling_dashboard.html",
                           user=counselor,
                           assigned_users=assigned_users)

@app.route("/awareness_dashboard")
def awareness_dashboard():
    if "counseling_user" not in session:
        flash(" Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["counseling_user"]
    counselor = db.reference("conseling_signup").child(counselor_id).get()

    if not counselor:
        flash("Counselor not found in database!", "danger")
        return redirect(url_for("counseling_signin"))



    #  Fetch awareness sessions directly
    all_sessions = db.reference("awareness_sessions").get() or {}
    sessions = {
        sid: sess for sid, sess in all_sessions.items()
        if isinstance(sess, dict) and sess.get("counselor_id") == counselor_id
    }

    return render_template(
        "awareness_dashboard.html",
        user=counselor,
        sessions=sessions
    )

# ---------------- Edit Awareness Profile ----------------
@app.route("/edit_awareness_profile", methods=["POST"])
def edit_awareness_profile():
    if "counseling_user" not in session:
        flash(" Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    user_id = session["counseling_user"]
    ref = db.reference("conseling_signup").child(user_id)

    user = ref.get()
    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("awareness_dashboard"))

    # Get form data
    new_name = request.form.get("name", user.get("name"))
    new_password = request.form.get("password", "").strip()

    # Update fields
    updates = {"name": new_name}
    if new_password:
        updates["password"] = new_password

    # Handle profile image upload
    if "profile_image" in request.files:
        image = request.files["profile_image"]
        if image.filename:
            # Save image to static/uploads/
            upload_path = os.path.join("static/uploads", image.filename)
            image.save(upload_path)
            updates["profile_image"] = f"uploads/{image.filename}"

    # Push updates to Firebase
    ref.update(updates)

    flash(" Profile updated successfully!", "success")
    return redirect(url_for("awareness_dashboard"))

@app.route("/create_awareness_session", methods=["GET", "POST"])
def create_awareness_session():
    if "counseling_user" not in session:
        flash(" Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["counseling_user"]
    counselor = db.reference("conseling_signup").child(counselor_id).get()
    users_ref = db.reference("users")
    users = users_ref.get() or {}

    if request.method == "POST":
        title = request.form.get("title")
        category = request.form.get("category")
        details = request.form.get("details")
        zoom_link = request.form.get("zoom_link")

        image_url = None
        if "image" in request.files:
            img = request.files["image"]
            if img.filename:
                path = os.path.join("static/uploads", img.filename)
                img.save(path)
                image_url = f"uploads/{img.filename}"

        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "counselor_id": counselor_id,
            "counselor_name": counselor.get("name"),
            "counselor_email": counselor.get("email"),
            "title": title,
            "category": category,
            "details": details,
            "zoom_link": zoom_link,
            "image": image_url,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "attendance": {}
        }
        db.reference("awareness_sessions").child(session_id).set(session_data)

        # Send emails + create attendance entries
        subject = f"New Awareness Session: {title}"
        body = f"""
        Dear Participant,

        You are invited to join our awareness session.

        Title: {title}
        Category: {category}
        Details: {details}
        Zoom Link: {zoom_link}

        Counselor: {counselor.get("name")}

        Regards,
        SahaaraX Team
        """
        for uid, usr in users.items():
            try:
                yag.send(usr["email"], subject, body)
                db.reference("awareness_sessions").child(session_id).child("attendance").child(uid).set({
                    "user_name": usr.get("name"),
                    "user_email": usr.get("email"),
                    "status": "Not Present"
                })
            except Exception as e:
                print("Email error:", e)

        flash(" Session created and invitations sent!", "success")
        return redirect(url_for("awareness_dashboard"))

    # Show dashboard sessions
    sessions = db.reference("awareness_sessions").get() or {}
    return render_template("awareness_dashboard.html", sessions=sessions)




@app.route("/view_session/<session_id>")
def view_session(session_id):
    session_data = db.reference("awareness_sessions").child(session_id).get()
    if not session_data:
        flash(" Session not found!", "danger")
        return redirect(url_for("awareness_dashboard"))
    return render_template("view_session.html", session=session_data)

@app.route("/mark_attendance/<session_id>", methods=["POST"])
def mark_attendance(session_id):
    if "counseling_user" not in session:
        flash(" Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    selected_present = request.form.getlist("present")
    ref = db.reference("awareness_sessions").child(session_id).child("attendance")
    attendance = ref.get() or {}

    for uid, att in attendance.items():
        status = "Present" if uid in selected_present else "Not Present"
        ref.child(uid).update({"status": status})

    flash(" Attendance updated!", "success")
    return redirect(url_for("awareness_dashboard"))

# ---------------- Manage Classes ----------------
@app.route("/counselor_class/<user_id>", methods=["GET", "POST"])
def counselor_class(user_id):
    if "counseling_user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    counselor_id = session["counseling_user"]
    counselor = db.reference("conseling_signup").child(counselor_id).get()
    user = db.reference("users").child(user_id).get()

    if not counselor or not user:
        return jsonify({"error": "Invalid user or counselor"}), 400

    #  Fetch existing classes (consistent path)
    classes_ref = db.reference("counseling_classes").child(counselor_id).child(user_id)
    existing_classes = classes_ref.get() or {}

    if request.method == "POST":
        date = request.form.get("date")
        time = request.form.get("time")

        if not date or not time:
            flash(" Please select date and time!", "danger")
            return redirect(url_for("counseling_dashboard"))

        class_id = str(uuid.uuid4())
        class_data = {
            "class_id": class_id,
            "counselor_id": counselor_id,
            "counselor_name": counselor.get("name"),
            "counselor_email": counselor.get("email"),
            "user_id": user_id,
            "user_name": user.get("name"),
            "user_email": user.get("email"),
            "date": date,
            "time": time,
            "status": "Scheduled",
            "start_time": None,
            "end_time": None,
            "attendance_count": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        #  Save class in proper structure
        db.reference("counseling_classes").child(counselor_id).child(user_id).child(class_id).set(class_data)

        # Send email to user
        subject = "New Counseling Class Scheduled"
        body = f"""
        Dear {user['name']},

        Your counseling class has been scheduled 

        Date: {date}  
        Time: {time}  
        Counselor: {counselor['name']}  

        Regards,  
        SahaaraX Team
        """
        try:
            yag.send(user["email"], subject, body)
        except Exception as e:
            print("Email error:", e)

        flash("Class scheduled and email sent!", "success")
        return redirect(url_for("counseling_dashboard"))

    return render_template("counselor_class_partial.html",
                           user=user,
                           counselor=counselor,
                           user_id=user_id,
                           classes=existing_classes)


# ---------------- Start Class ----------------
@app.route("/start_class/<counselor_id>/<user_id>/<class_id>")
def start_class(counselor_id, user_id, class_id):
    ref = db.reference("counseling_classes").child(counselor_id).child(user_id).child(class_id)
    class_data = ref.get()

    if not class_data:
        flash("Class not found!", "danger")
        return redirect(url_for("counseling_dashboard"))

    #  Update start time
    ref.update({
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Ongoing"
    })

    flash(f"Class started with {class_data['user_name']}", "success")
    return redirect(url_for("counselor_class", user_id=user_id))


# ---------------- End Class ----------------
@app.route("/end_class/<counselor_id>/<user_id>/<class_id>")
def end_class(counselor_id, user_id, class_id):
    ref = db.reference("counseling_classes").child(counselor_id).child(user_id).child(class_id)
    class_data = ref.get()

    if not class_data:
        flash("Class not found!", "danger")
        return redirect(url_for("counseling_dashboard"))

    #  Update end time + attendance
    attendance = class_data.get("attendance_count", 0) + 1
    ref.update({
        "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Completed",
        "attendance_count": attendance
    })

    flash(f"Class completed for {class_data['user_name']}. Attendance updated.", "success")
    return redirect(url_for("counselor_class", user_id=user_id))


genai.configure(api_key="AIzaSyB3VgAik36l1ZjSATlYY_p3jUkpAq8_Po4")

@app.route("/attendance/<user_id>")
def attendance(user_id):
    if "counseling_user" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("counseling_signin"))

    counselor_id = session["counseling_user"]

    #  Go directly to counselor_id → user_id → class list
    classes_ref = db.reference("counseling_classes").child(counselor_id).child(user_id)
    classes = classes_ref.get() or {}

    #  Count completed classes
    attendance_count = sum(1 for cid, c in classes.items() if c.get("status") == "Completed")

    #  Unlock test if 3+ completed
    test_unlocked = attendance_count >= 3

    return render_template(
        "attendance.html",
        classes=classes,
        user_id=user_id,
        test_unlocked=test_unlocked,
        attendance_count=attendance_count
    )



@app.route("/start_test/<user_id>", methods=["GET", "POST"])
def start_test(user_id):
    if request.method == "POST":
        category = request.form.get("category")

        if not category:
            flash(" Please select a category.", "danger")
            return redirect(url_for("start_test", user_id=user_id))

        # Prompt for Gemini
        prompt = f"""
        Create a counseling test with exactly 5 multiple-choice questions 
        about {category}.

        Each question must include:
        - "question" (string)
        - "options" (array of 4 strings like "A) ...", "B) ...")
        - "answer" (correct option letter)

        Respond ONLY in valid JSON array, no markdown, no explanations.
        """

        # Call Gemini
        response = model.generate_content(prompt)

        # Clean output (Gemini kabhi ```json ... ``` bhejta hai)
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1].replace("json", "").strip()

        try:
            questions = json.loads(raw_text)
        except Exception as e:
            print(" JSON Parse Error:", e, "RAW:", raw_text)
            flash("Error generating questions from AI.", "danger")
            return redirect(url_for("attendance", user_id=user_id))

        # Save to Firebase
        test_id = str(uuid.uuid4())
        db.reference("counseling_tests").child(user_id).child(test_id).set({
            "category": category,
            "questions": questions,
            "status": "Pending"
        })

        return render_template(
            "test.html",
            user_id=user_id,
            test_id=test_id,
            category=category,
            questions=questions
        )

    # GET: show category selection form
    return render_template("start_test.html", user_id=user_id)

# ---------------- SUBMIT TEST ----------------
@app.route("/submit_test/<user_id>/<test_id>", methods=["POST"])
def submit_test(user_id, test_id):
    answers = {}
    for key, val in request.form.items():
        answers[key] = val

    # Get test details
    test_ref = db.reference("counseling_tests").child(user_id).child(test_id)
    test_data = test_ref.get()

    if not test_data:
        flash("Test not found!", "danger")
        return redirect(url_for("attendance", user_id=user_id))

    # Send answers to Gemini for evaluation
    prompt = f"""
    A patient has taken a counseling test on {test_data['category']}.
    Questions: {test_data['questions']}
    Answers: {answers}

    Based on the answers, provide:
    1. A short psychological evaluation.
    2. Recommendations: Should the patient continue counseling or take further actions?
    """

    model = genai.GenerativeModel("gemini-1.5-flash")
    result = model.generate_content(prompt)

    evaluation = result.text

    # Save result in Firebase
    test_ref.update({
        "answers": answers,
        "evaluation": evaluation,
        "status": "Completed"
    })
    return render_template("test_result.html",
                           user_id=user_id,
                           test_id=test_id,
                           evaluation=evaluation)

# ---------------- View Counseling Users ----------------
@app.route("/view_counseling", methods=["GET"])
def view_counseling():
    # Get filters from query params
    counseling_filter = request.args.get("counseling", "All")
    gender_filter = request.args.get("gender", "All")
    availability_filter = request.args.get("availability", "All")
    location_filter = request.args.get("location", "").strip()

    # Fetch users
    ref = db.reference("conseling_signup")
    all_users = ref.get() or {}

    filtered_users = {}
    for uid, user in all_users.items():
        # Skip incomplete data
        if not user.get("name") or not user.get("counseling"):
            continue

        # Apply filters
        if counseling_filter != "All" and user.get("counseling") != counseling_filter:
            continue
        if gender_filter != "All" and user.get("gender") != gender_filter:
            continue
        if availability_filter != "All" and user.get("availability") != availability_filter:
            continue
        if location_filter and location_filter.lower() not in user.get("location", "").lower():
            continue

        filtered_users[uid] = user

    return render_template(
        "view_counseling.html",
        users=filtered_users,
        filter_counseling=counseling_filter,
        filter_gender=gender_filter,
        filter_availability=availability_filter,
        filter_location=location_filter
    )

@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("admin_login"))

@app.route("/success-stories")
def gallery():
    return render_template("gallery.html")

@app.route("/gallery")
def gal():
    return render_template("gallery.html")

@app.route("/ripple")
def ripple():
    return render_template("ripple.html")
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/services")
def services():
    return render_template("services.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not subject or not message:
            flash(" Please fill all fields.", "danger")
            return redirect(url_for("contact"))

        # Email Content
        email_subject = f" New Contact Form Message: {subject}"
        email_body = f"""
        You have received a new message from the SahaaraX Contact Form.

        👤 Name: {name}
        📧 Email: {email}
        📝 Subject: {subject}
        💬 Message:
        {message}

        -----------------------------
        This email was sent automatically by SahaaraX system.
        """

        try:
            yag.send(
                to="saharaax2468@gmail.com",
                subject=email_subject,
                contents=email_body
            )
            flash(" Your message has been sent successfully! We will get back to you soon.", "success")
        except Exception as e:
            print("❌ Email error:", e)
            flash(" Failed to send message. Please try again later.", "danger")

        return redirect(url_for("contact"))

    return render_template("contact.html")

@app.route("/attendance_report")
def attendance_report():
    all_sessions = db.reference("awareness_sessions").get() or {}
    user_summary = {}

    total_present = 0
    total_absent = 0
    total_sessions = 0

    for session_id, sess in (all_sessions or {}).items():
        if not isinstance(sess, dict):
            continue

        session_title = sess.get("title", "Untitled Session")
        session_category = sess.get("category", "Unknown")
        attendance = sess.get("attendance", {})

        for uid, att in (attendance or {}).items():
            user_email = att.get("user_email", "unknown")
            user_name = att.get("user_name", "Unknown User")
            status = att.get("status", "Absent")

            if uid not in user_summary:
                user_summary[uid] = {
                    "name": user_name,
                    "email": user_email,
                    "total_sessions": 0,
                    "present_count": 0,
                    "absent_count": 0,
                    "sessions": []
                }

            # Update counts
            user_summary[uid]["total_sessions"] += 1
            total_sessions += 1

            if status == "Present":
                user_summary[uid]["present_count"] += 1
                total_present += 1
            else:
                user_summary[uid]["absent_count"] += 1
                total_absent += 1

            # Store session details
            user_summary[uid]["sessions"].append({
                "title": session_title,
                "category": session_category,
                "status": status,
                "created_at": sess.get("created_at", "")
            })

    # Highcharts summary data
    chart_data = {
        "total_sessions": total_sessions,
        "present": total_present,
        "absent": total_absent,
    }

    return render_template(
        "attendance_report.html",
        users=list(user_summary.values()),
        chart_data=chart_data
    )

@app.route("/admin_report")
def admin_report():
    # Awareness Sessions Attendance
    all_awareness = db.reference("awareness_sessions").get() or {}
    awareness_summary = {}
    total_awareness_present = total_awareness_absent = 0

    for session_id, sess in all_awareness.items():
        attendance = sess.get("attendance", {})
        for uid, att in attendance.items():
            name = att.get("user_name", "Unknown")
            email = att.get("user_email", "Unknown")
            status = att.get("status", "Not Present")

            if uid not in awareness_summary:
                awareness_summary[uid] = {
                    "name": name,
                    "email": email,
                    "sessions": 0,
                    "present": 0,
                    "absent": 0
                }

            awareness_summary[uid]["sessions"] += 1
            if status == "Present":
                awareness_summary[uid]["present"] += 1
                total_awareness_present += 1
            else:
                awareness_summary[uid]["absent"] += 1
                total_awareness_absent += 1

    # Counseling Classes
    counseling_data = db.reference("counseling_classes").get() or {}
    counseling_summary = {}
    total_classes = 0
    for counselor_id, users in counseling_data.items():
        for user_id, classes in users.items():
            for class_id, cls in classes.items():
                name = cls.get("user_name", "Unknown")
                email = cls.get("user_email", "Unknown")

                if user_id not in counseling_summary:
                    counseling_summary[user_id] = {
                        "name": name,
                        "email": email,
                        "classes": 0
                    }

                counseling_summary[user_id]["classes"] += 1
                total_classes += 1

    # Shelter Beds
    rooms = db.reference("rooms").get() or {}
    total_beds = available_beds = 0
    for room_id, room in rooms.items():
        total_beds += room.get("bed_count", 0)
        available_beds += room.get("available_beds", 0)
    occupied_beds = total_beds - available_beds

    # Other Counts
    total_users = len(db.reference("users").get() or {})
    total_counselors = len(db.reference("conseling_signup").get() or {})
    total_sessions = len(all_awareness)

    dashboard_counts = {
        "total_users": total_users,
        "total_counselors": total_counselors,
        "total_beds": total_beds,
        "available_beds": available_beds,
        "occupied_beds": occupied_beds,
        "total_awareness_sessions": total_sessions,
        "total_awareness_present": total_awareness_present,
        "total_awareness_absent": total_awareness_absent,
        "total_counseling_classes": total_classes,
    }

    # Chart Data for Highcharts
    chart_data = {
        "awareness": {
            "present": total_awareness_present,
            "absent": total_awareness_absent,
        },
        "beds": {
            "available": available_beds,
            "occupied": occupied_beds,
        }
    }

    return render_template(
        "admin_report.html",
        awareness_summary=awareness_summary,
        counseling_summary=counseling_summary,
        dashboard_counts=dashboard_counts,
        chart_data=chart_data
    )

@app.route("/user_progress")
def user_progress():
    # Awareness Sessions
    all_awareness = db.reference("awareness_sessions").get() or {}
    progress_summary = {}

    for session_id, sess in (all_awareness or {}).items():
        if not isinstance(sess, dict):
            continue

        session_title = sess.get("title", "Untitled Session")
        session_category = sess.get("category", "Unknown")
        attendance = sess.get("attendance", {})

        for uid, att in (attendance or {}).items():
            name = att.get("user_name", "Unknown")
            email = att.get("user_email", "unknown")
            status = att.get("status", "Not Present")

            if uid not in progress_summary:
                progress_summary[uid] = {
                    "name": name,
                    "email": email,
                    "sessions": 0,
                    "present": 0,
                    "absent": 0,
                    "details": []
                }

            progress_summary[uid]["sessions"] += 1
            if status == "Present":
                progress_summary[uid]["present"] += 1
            else:
                progress_summary[uid]["absent"] += 1

            progress_summary[uid]["details"].append({
                "session": session_title,
                "category": session_category,
                "status": status,
                "created_at": sess.get("created_at", "")
            })

    # Calculate progress percentage
    for uid, data in progress_summary.items():
        if data["sessions"] > 0:
            data["progress_percent"] = round((data["present"] / data["sessions"]) * 100, 1)
        else:
            data["progress_percent"] = 0

    return render_template("user_progress.html", users=progress_summary)


@app.route('/admin/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'admin' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('admin_login'))

    admin_email = session['admin'].strip()

    ref = db.reference('admin')
    admin_data = ref.get()  # {'email': ..., 'password': ...}

    if not isinstance(admin_data, dict):
        flash('Invalid admin data structure.', 'danger')
        return redirect(url_for('admin_dashboard'))

    #  Check if the session email matches Firebase email
    if admin_data.get('email', '').strip() != admin_email:
        flash('Session does not match admin data.', 'danger')
        return redirect(url_for('admin_dashboard'))

    #  If POST: update values
    if request.method == 'POST':
        updated_email = request.form.get('email', '').strip()
        updated_password = request.form.get('password', '').strip()

        if not updated_email or not updated_password:
            flash('Email and password are required.', 'danger')
            return redirect(url_for('edit_profile'))

        try:
            ref.update({
                'email': updated_email,
                'password': updated_password
            })
            session['admin'] = updated_email
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

        return redirect(url_for('edit_profile'))

    #  GET request — render form
    return render_template('edit_profile.html', admin=admin_data)

@app.route("/all_counselors", methods=["GET", "POST"])
def all_counselors():
    ref = db.reference("conseling_signup")
    counselors = ref.get() or {}

    # Filters
    filter_type = request.args.get("type", "").strip()
    filter_gender = request.args.get("gender", "").strip()
    filter_location = request.args.get("location", "").strip()

    filtered = {}
    for cid, c in counselors.items():
        if not isinstance(c, dict):
            continue
        # Apply filters
        if filter_type and c.get("counseling") != filter_type:
            continue
        if filter_gender and c.get("gender") != filter_gender:
            continue
        if filter_location and filter_location.lower() not in c.get("location", "").lower():
            continue

        filtered[cid] = c

    return render_template(
        "all_counselors.html",
        counselors=filtered,
        filter_type=filter_type,
        filter_gender=filter_gender,
        filter_location=filter_location,
    )

@app.route("/donate", methods=["GET", "POST"])
def donate():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        amount = request.form.get("amount")
        message = request.form.get("message")

        if not name or not email or not amount:
            flash(" Please fill all required fields.", "danger")
            return redirect(url_for("donate"))

        # Save to Firebase
        ref = db.reference("donations")
        donation_id = str(uuid.uuid4())
        ref.child(donation_id).set({
            "name": name,
            "email": email,
            "phone": phone,
            "amount": amount,
            "message": message,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        flash(" Thank you for your donation!", "success")
        return redirect(url_for("donate"))

    return render_template("donate.html")
@app.route("/volunteer", methods=["GET", "POST"])
def volunteer():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        skills = request.form.get("skills")
        availability = request.form.get("availability")
        message = request.form.get("message")

        if not name or not email or not phone:
            flash(" Please fill all required fields.", "danger")
            return redirect(url_for("volunteer"))

        ref = db.reference("volunteers")
        volunteer_id = str(uuid.uuid4())
        ref.child(volunteer_id).set({
            "name": name,
            "email": email,
            "phone": phone,
            "skills": skills,
            "availability": availability,
            "message": message,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        flash(" Thank you for joining as a Volunteer!", "success")
        return redirect(url_for("volunteer"))

    return render_template("volunteer.html")


@app.route("/emergency_Alert", methods=["GET", "POST"])
def emergency_alert():
    if request.method == "POST":
        ref = db.reference("users")
        users = ref.get() or {}

        #  Sirf approved users ko bhejna
        approved_users = {
            uid: u for uid, u in users.items()
            if u.get("status", "").lower() == "approved"
        }

        #  Email setup
        yag = yagmail.SMTP("saharax191@gmail.com", "ctravpkafztcmjiu")

        #  Email content
        subject = "🚨 Emergency Aid Alert - SahaaraX"
        body = """
        Dear User,

        This is an important notification from SahaaraX.
        Emergency aid has been activated. Please contact our support team immediately 
        or visit SahaaraX shelter Emergency AID.

        Stay safe,  
        SahaaraX Team
        """

        sent_count = 0

        for uid, user in approved_users.items():
            try:
                yag.send(user["email"], subject, body)

                db.reference("emergency_aid").child(uid).push({
                    "email": user["email"],
                    "name": user["name"],
                    "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                sent_count += 1
            except Exception as e:
                print(f" Error sending to {user['email']}: {str(e)}")

        flash(f" Emergency Aid emails sent to {sent_count} approved users.", "success")
        return redirect(url_for("emergency_alert"))

    return render_template("emergency_aid.html")

@app.route("/add_course", methods=["GET", "POST"])
def add_course():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()

        if not title or not category:
            flash(" All fields are required!", "danger")
            return redirect(url_for("add_course"))

        # Dynamically collect lecture links
        lectures = []
        for key in request.form:
            if key.startswith("lecture_"):
                url = request.form.get(key).strip()
                if url:
                    lectures.append(url)

        if not lectures:
            flash(" Please add at least one lecture link.", "danger")
            return redirect(url_for("add_course"))

        # Save to Firebase
        course_id = str(uuid.uuid4())
        db.reference("courses").child(course_id).set({
            "title": title,
            "category": category,
            "lectures": lectures
        })

        flash(" Course added successfully!", "success")
        return redirect(url_for("view_courses"))

    return render_template("add_course.html")


@app.route("/view_courses")
def view_courses():
    ref = db.reference("courses")
    courses = ref.get() or {}

    return render_template("view_courses.html", courses=courses)
@app.route("/legal_support_cases")
def legal_support_cases():
    ref = db.reference("users")
    users = ref.get() or {}

    # Filter users who are approved AND have 'legal' in their categories
    legal_users = {
        uid: u for uid, u in users.items()
        if u.get("status") == "Approved" and "legal" in (u.get("categories") or [])
    }

    return render_template("legal_support_cases.html", users=legal_users)

@app.route("/assign_lawyer/<user_id>", methods=["GET", "POST"])
def assign_lawyer(user_id):
    user = db.reference("users").child(user_id).get()
    if not user:
        flash("User not found!", "danger")
        return redirect(url_for("legal_support_cases"))

    if request.method == "POST":
        lawyer_name = request.form.get("lawyer_name").strip()
        lawyer_email = request.form.get("lawyer_email").strip()

        if not lawyer_name or not lawyer_email:
            flash("Please enter both lawyer name and email.", "danger")
            return redirect(url_for("assign_lawyer", user_id=user_id))

        # Save assignment in Firebase
        assignment = {
            "user_id": user_id,
            "user_name": user["name"],
            "user_email": user["email"],
            "case_details": user["description"],
            "lawyer_name": lawyer_name,
            "lawyer_email": lawyer_email,
            "timestamp": str(datetime.now())
        }
        db.reference("assigned_lawyers").push(assignment)

        # Send email to user
        subject = "⚖️ Legal Support Assigned - SahaaraX"
        body = f"""
        Dear {user['name']},

        A legal support officer has been assigned to your case.

        🧑‍⚖️ Lawyer: {lawyer_name}  
        📧 Email: {lawyer_email}

        They will contact you soon regarding your legal support request.

        Regards,  
        SahaaraX Team
        """
        try:
            yag.send(user["email"], subject, body)
        except Exception as e:
            flash(" Failed to send email.", "warning")
            print("Email error:", e)

        flash(" Lawyer assigned and user notified.", "success")
        return redirect(url_for("legal_support_cases"))

    return render_template("assign_lawyer.html", user=user)


@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()

    if not email:
        flash(" Please enter a valid email.", "danger")
        return redirect(request.referrer or url_for("home"))

    try:
        ref = db.reference("subscribers")
        subscribers = ref.get() or {}

        #  Check if email already exists
        for sid, sub in subscribers.items():
            if sub.get("email") == email:
                flash("⚠️ This email is already subscribed!", "warning")
                return redirect(request.referrer or url_for("home"))

        #  Add new subscriber
        subscriber_id = str(uuid.uuid4())
        ref.child(subscriber_id).set({
            "email": email,
            "subscribed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        flash(" Thank you for subscribing!", "success")
        return redirect(request.referrer or url_for("home"))

    except Exception as e:
        print("🔥 Firebase Error:", e)
        flash(" Could not connect to database. Try again later.", "danger")
        return redirect(request.referrer or url_for("home"))


@app.route("/subscribers", methods=["GET", "POST"])
def subscribers():
    ref = db.reference("subscribers")
    subscribers = ref.get() or {}

    total_subscribers = len(subscribers)

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not subject or not message:
            flash(" Please enter subject and message.", "danger")
            return redirect(url_for("subscribers"))

        emails = [sub.get("email") for sub in subscribers.values() if sub.get("email")]

        if not emails:
            flash(" No subscribers found!", "warning")
            return redirect(url_for("subscribers"))

        #  Initialize yagmail once
        yag = yagmail.SMTP("saharax191@gmail.com", "ctravpkafztcmjiu")

        sent_count = 0
        failed_count = 0

        for email in emails:
            try:
                yag.send(
                    to=email,
                    subject=subject,
                    contents=f"""
                    Dear Subscriber,

                    {message}

                    Regards,
                    SahaaraX Team
                    """
                )
                sent_count += 1
            except Exception as e:
                print(f" Error sending to {email}: {e}")
                failed_count += 1

        flash(f" Newsletter sent to {sent_count} subscribers! ❌ Failed: {failed_count}", "success")
        return redirect(url_for("subscribers"))

    return render_template("subscribers.html", subscribers=subscribers, total_subscribers=total_subscribers)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
