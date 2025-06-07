import re
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    g,
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SelectField,
    validators,
    HiddenField,
    TextAreaField,
)
import sqlite3
import os
import math
import re

SIGN_UP_TEMPLATE = "sign_up.html"
SIGN_IN_TEMPLATE = "sign_in.html"

app = Flask(__name__)
# Basit bir secret key
app.config["SECRET_KEY"] = "development-key"
app.config["WTF_CSRF_ENABLED"] = False


# Session ayarları
@app.before_request
def before_request():
    session.permanent = True  # Session'ı kalıcı yap


DB_PATH = "data.db"


def get_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Veritabanı bağlantı hatası: {str(e)}")
        raise


def close_db(conn):
    if conn is not None:
        try:
            conn.close()
        except sqlite3.Error as e:
            print(f"Veritabanı kapatma hatası: {str(e)}")


@app.teardown_appcontext
def teardown_db(exception):
    conn = getattr(g, "_database", None)
    if conn is not None:
        close_db(conn)


# Form sınıfları
class SignUpForm(FlaskForm):
    fullname = StringField(
        "Ad Soyad",
        [
            validators.DataRequired(message="Ad Soyad alanı zorunludur."),
            validators.Length(
                min=3, max=50, message="Ad Soyad 3-50 karakter arasında olmalıdır."
            ),
        ],
    )
    username = StringField(
        "Kullanıcı Adı",
        [
            validators.DataRequired(message="Kullanıcı adı zorunludur."),
            validators.Length(
                min=3, max=20, message="Kullanıcı adı 3-20 karakter arasında olmalıdır."
            ),
            validators.Regexp(
                r"^[a-zA-Z0-9_]+$",
                message="Kullanıcı adı sadece harf, rakam ve alt çizgi içerebilir.",
            ),
        ],
    )
    email = StringField(
        "E-posta",
        [
            validators.DataRequired(message="E-posta alanı zorunludur."),
            validators.Email(message="Geçerli bir e-posta adresi giriniz."),
        ],
    )
    phone = StringField(
        "Telefon (İsteğe bağlı)",
        [
            validators.Optional(),
            validators.Regexp(
                r"^\+?1?\d{9,15}$", message="Geçerli bir telefon numarası giriniz."
            ),
        ],
    )
    password = PasswordField(
        "Şifre",
        [
            validators.DataRequired(message="Şifre alanı zorunludur."),
            validators.Length(
                min=4, message="Şifre en az 4 karakter uzunluğunda olmalıdır."
            ),
        ],
    )
    role = SelectField(
        "Rol",
        [validators.DataRequired(message="Rol seçimi zorunludur.")],
        choices=[
            ("volunteer", "Gönüllü"),
            ("requester", "Afetzede"),
        ],
    )


class HelpRequestForm(FlaskForm):
    disasterType = SelectField(
        "Afet Türü",
        [validators.DataRequired(message="Lütfen bir afet türü seçiniz.")],
        choices=[],
    )
    lat = HiddenField(
        "Enlem", [validators.DataRequired(message="Konum bilgisi gereklidir.")]
    )
    lng = HiddenField(
        "Boylam", [validators.DataRequired(message="Konum bilgisi gereklidir.")]
    )
    province = SelectField(
        "İl",
        [validators.Optional()],
        choices=[],
        coerce=lambda x: int(x) if x else None,
    )
    district = SelectField(
        "İlçe",
        [validators.Optional()],
        choices=[],
        coerce=lambda x: int(x) if x else None,
    )
    neighborhood = SelectField(
        "Mahalle",
        [validators.Optional()],
        choices=[],
        coerce=lambda x: int(x) if x else None,
    )
    street = SelectField(
        "Sokak",
        [validators.Optional()],
        choices=[],
        coerce=lambda x: int(x) if x else None,
    )
    additional_info = TextAreaField("Ek Bilgiler", [validators.Optional()])


# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/help", methods=["GET", "POST"])
def help_request():
    conn = None
    try:
        # Veri tabanından disaster türlerini çekme
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, name FROM disaster_types")
        disaster_types = c.fetchall()

        # Form oluştur
        form = HelpRequestForm()

        # Afet türü seçeneklerini ayarla
        choices = [("", "Lütfen bir afet türü seçiniz")]
        if disaster_types:
            choices.extend([(str(dt[0]), dt[1]) for dt in disaster_types])
        else:
            choices.append(("", "Afet türü bulunamadı"))

        form.disasterType.choices = choices

        # İl seçeneklerini doldur
        c.execute(
            "SELECT province_id, province_name FROM provinces ORDER BY province_name"
        )
        provinces = c.fetchall()
        form.province.choices = [("", "Şehir seçiniz")] + [
            (str(p[0]), p[1]) for p in provinces
        ]

        if request.method == "POST":
            print("POST request received")
            print("Form data:", request.form)
            print("Headers:", request.headers)

            # İl seçilmişse ilçeleri doldur
            if form.province.data:
                c.execute(
                    "SELECT district_id, district_name FROM districts WHERE province_id = ? ORDER BY district_name",
                    (form.province.data,),
                )
                districts = c.fetchall()
                form.district.choices = [("", "İlçe seçiniz")] + [
                    (str(d[0]), d[1]) for d in districts
                ]

            # İlçe seçilmişse mahalleleri doldur
            if form.district.data:
                c.execute(
                    "SELECT neighborhood_id, neighborhood_name FROM neighborhoods WHERE district_id = ? ORDER BY neighborhood_name",
                    (form.district.data,),
                )
                neighborhoods = c.fetchall()
                form.neighborhood.choices = [("", "Mahalle seçiniz")] + [
                    (str(n[0]), n[1]) for n in neighborhoods
                ]

            # Mahalle seçilmişse sokakları doldur
            if form.neighborhood.data:
                c.execute(
                    "SELECT street_id, street_name FROM streets WHERE neighborhood_id = ? ORDER BY street_name",
                    (form.neighborhood.data,),
                )
                streets = c.fetchall()
                form.street.choices = [("", "Sokak seçiniz")] + [
                    (str(s[0]), s[1]) for s in streets
                ]

            if form.validate():
                print("Form validation successful")
                disaster_type = form.disasterType.data
                lat = form.lat.data
                lng = form.lng.data
                province_id = form.province.data
                district_id = form.district.data
                neighborhood_id = form.neighborhood.data
                street_id = form.street.data
                additional_info = form.additional_info.data or ""

                try:
                    # Önce location kaydı oluştur
                    c.execute(
                        "INSERT INTO locations(province_id, district_id, neighborhood_id, street_id, latitude, longitude) VALUES (?,?,?,?,?,?)",
                        (
                            province_id,
                            district_id,
                            neighborhood_id,
                            street_id,
                            lat,
                            lng,
                        ),
                    )
                    location_id = c.lastrowid
                    print(f"Location created with ID: {location_id}")

                    # Sonra disaster kaydı oluştur
                    c.execute(
                        "INSERT INTO disasters(disaster_type_id, location_id, description, started_at) VALUES (?,?,?,CURRENT_TIMESTAMP)",
                        (disaster_type, location_id, additional_info),
                    )
                    disaster_id = c.lastrowid
                    print(f"Disaster created with ID: {disaster_id}")

                    # Son olarak help_request kaydı oluştur
                    c.execute(
                        "INSERT INTO help_requests(requester_id, location_id, additional_info, status) VALUES (?,?,?,?)",
                        (
                            session.get("user_id"),
                            location_id,
                            additional_info,
                            "pending",
                        ),
                    )
                    print("Help request created successfully")

                    conn.commit()

                    # Afet türünün adını al
                    c.execute(
                        "SELECT name FROM disaster_types WHERE id = ?", (disaster_type,)
                    )
                    disaster_name = c.fetchone()[0]

                    if request.headers.get("Accept") == "application/json":
                        response = jsonify(
                            {
                                "success": True,
                                "message": "Yardım talebiniz başarıyla alındı.",
                                "redirect_url": url_for(
                                    "help_sended", disaster_name=disaster_name
                                ),
                            }
                        )
                        print("Sending JSON response:", response.get_data(as_text=True))
                        return response

                    flash("Yardım talebiniz başarıyla alındı.", "success")
                    return render_template("help_sended.html", data=disaster_name)
                except Exception as e:
                    conn.rollback()
                    print(f"Database error: {str(e)}")
                    if request.headers.get("Accept") == "application/json":
                        response = (
                            jsonify(
                                {
                                    "success": False,
                                    "message": f"Yardım talebi gönderilirken bir hata oluştu: {str(e)}",
                                }
                            ),
                            500,
                        )
                        print(
                            "Sending error JSON response:",
                            response[0].get_data(as_text=True),
                        )
                        return response

                    flash(
                        "Yardım talebi gönderilirken bir hata oluştu. Lütfen tekrar deneyin.",
                        "error",
                    )
                    return render_template(
                        "help.html", form=form, disaster_types=disaster_types
                    )
            else:
                print("Form validation failed:", form.errors)
                if request.headers.get("Accept") == "application/json":
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "Form doğrulama hatası",
                                "errors": form.errors,
                            }
                        ),
                        400,
                    )

        return render_template("help.html", form=form, disaster_types=disaster_types)
    except Exception as e:
        print(f"Unexpected error in help_request: {str(e)}")
        if request.headers.get("Accept") == "application/json":
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Beklenmeyen bir hata oluştu: {str(e)}",
                    }
                ),
                500,
            )
        raise
    finally:
        if conn is not None:
            close_db(conn)


@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    form = SignUpForm()
    if form.validate_on_submit():
        conn = None
        try:
            conn = get_db()
            c = conn.cursor()

            # Kullanıcı adının ve e-posta adresinin benzersizliğini ayrı ayrı kontrol et
            username_exists = False
            email_exists = False

            # Kullanıcı adının benzersizliğini kontrol et
            c.execute("SELECT id FROM users WHERE username = ?", (form.username.data,))
            if c.fetchone():
                username_exists = True
                flash("Bu kullanıcı adı zaten kullanılıyor.", "error")

            # E-posta adresinin benzersizliğini kontrol et
            c.execute("SELECT id FROM users WHERE email = ?", (form.email.data,))
            if c.fetchone():
                email_exists = True
                flash("Bu e-posta adresi zaten kullanılıyor.", "error")

            # Eğer kullanıcı adı veya e-posta zaten varsa kayıt işlemini durdur
            if username_exists or email_exists:
                return render_template(SIGN_UP_TEMPLATE, form=form)

            # Koordinatör rolü kısıtlaması
            if form.role.data == "coordinator":
                flash(
                    "Koordinatör hesabı açmak için lütfen sistem yöneticisi ile iletişime geçin.",
                    "warning",
                )
                return render_template(SIGN_UP_TEMPLATE, form=form)

            # Rol ID'sini al
            c.execute("SELECT id FROM roles WHERE name = ?", (form.role.data,))
            role = c.fetchone()
            if not role:
                flash("Geçersiz rol seçimi.", "error")
                return render_template(SIGN_UP_TEMPLATE, form=form)

            # Yeni kullanıcı oluştur
            c.execute(
                """
                INSERT INTO users (fullname, username, email, phone, password_hash, role_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    form.fullname.data,
                    form.username.data,
                    form.email.data,
                    form.phone.data,
                    generate_password_hash(form.password.data),
                    role["id"],
                ),
            )
            conn.commit()
            flash("Kayıt başarılı! Şimdi giriş yapabilirsiniz.", "success")
            return redirect(url_for("sign_in"))
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            flash(
                "Kayıt sırasında bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                "error",
            )
            return render_template(SIGN_UP_TEMPLATE, form=form)
        finally:
            if conn:
                close_db(conn)

    # Form hatalarını göster
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", "error")

    return render_template(SIGN_UP_TEMPLATE, form=form)


@app.route("/sign_in", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        login = request.form["login"]
        pwd = request.form["password"]

        if not login or not pwd:
            flash(
                "Lütfen giriş bilgilerinizi ve şifre alanını doldurunuz.", "login_error"
            )
            return render_template(SIGN_IN_TEMPLATE)

        conn = None
        try:
            conn = get_db()
            c = conn.cursor()

            # First get the user's password hash
            c.execute(
                """
                SELECT u.id, r.name as role, u.password_hash 
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.email = ? OR u.username = ?
                """,
                (login, login),
            )
            user = c.fetchone()

            if user and check_password_hash(user[2], pwd):  # user[2] is password_hash
                session["user_id"], session["role"] = user[0], user[1]
                # Son giriş zamanını güncelle
                c.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP, is_active = 1 WHERE id = ?",
                    (user[0],),
                )
                conn.commit()
                return redirect(url_for(f"{user[1]}_panel"))
            else:
                flash("Giriş bilgileri veya şifre hatalı.", "login_error")
                return render_template(SIGN_IN_TEMPLATE)
        except sqlite3.Error as e:
            print(f"Giriş sırasında veritabanı hatası: {str(e)}")
            flash(
                "Giriş yapılırken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                "error",
            )
            return render_template(SIGN_IN_TEMPLATE)
        finally:
            if conn:
                close_db(conn)

    return render_template(SIGN_IN_TEMPLATE)


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


@app.route("/volunteer-panel", methods=["GET", "POST"])
def volunteer_panel():
    if session.get("role") != "volunteer":
        return redirect(url_for("sign_in"))

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        request_id = request.form.get("request_id")
        action = request.form.get("action")

        if request_id and action in ["accept", "cancel"]:
            if action == "accept":
                # Check if already assigned
                c.execute(
                    "SELECT id FROM assignments WHERE request_id = ? AND volunteer_id = ?",
                    (request_id, session["user_id"]),
                )
                if not c.fetchone():
                    c.execute(
                        """
                        INSERT INTO assignments (request_id, volunteer_id, accepted)
                        VALUES (?, ?, 1)
                    """,
                        (request_id, session["user_id"]),
                    )
                    flash("Yardım isteğini kabul ettiniz.", "success")
            else:  # cancel
                c.execute(
                    """
                    DELETE FROM assignments 
                    WHERE request_id = ? AND volunteer_id = ?
                """,
                    (request_id, session["user_id"]),
                )
                flash("Yardım isteğinden çekildiniz.", "info")

            conn.commit()

    # Get volunteer's location first
    c.execute(
        """
        SELECT l.latitude, l.longitude
        FROM volunteer_details vd
        LEFT JOIN locations l ON vd.location_id = l.id
        WHERE vd.user_id = ?
        """,
        (session["user_id"],),
    )
    volunteer_location = c.fetchone()

    if (
        not volunteer_location
        or volunteer_location[0] is None
        or volunteer_location[1] is None
    ):
        flash("Lütfen önce konum bilgilerinizi güncelleyin.", "warning")
        conn.close()
        return redirect(url_for("profile"))

    volunteer_lat, volunteer_lon = volunteer_location

    # Get pending requests within 50km radius
    c.execute(
        """
        SELECT hr.id, l.latitude, l.longitude, hr.status, hr.additional_info, 
               dt.name as disaster_type, hr.created_at,
               p.province_name, d.district_name,
               (SELECT COUNT(*) FROM assignments a WHERE a.request_id = hr.id) as volunteer_count
        FROM help_requests hr
        JOIN locations l ON hr.location_id = l.id
        JOIN disasters d ON d.location_id = l.id
        JOIN disaster_types dt ON d.disaster_type_id = dt.id
        LEFT JOIN provinces p ON l.province_id = p.province_id
        LEFT JOIN districts d ON l.district_id = d.district_id
        WHERE hr.status = 'pending'
        ORDER BY hr.created_at DESC
    """
    )
    all_pending_requests = c.fetchall()

    # Filter requests based on distance and sort by proximity
    MAX_DISTANCE = 50  # 50 kilometers
    pending_requests = []
    for req in all_pending_requests:
        distance = haversine_distance(
            volunteer_lat, volunteer_lon, req["latitude"], req["longitude"]
        )
        if distance <= MAX_DISTANCE:
            req_dict = dict(req)
            req_dict["distance"] = round(distance, 1)
            pending_requests.append(req_dict)
    
    # Sort by distance (closest first)
    pending_requests.sort(key=lambda x: x["distance"])

    # Get accepted requests by this volunteer
    c.execute(
        """
        SELECT hr.id, l.latitude, l.longitude, hr.status, hr.additional_info, 
               dt.name as disaster_type, hr.created_at,
               p.province_name, d.district_name,
               a.completed_at
        FROM help_requests hr
        JOIN locations l ON hr.location_id = l.id
        JOIN disasters d ON d.location_id = l.id
        JOIN disaster_types dt ON d.disaster_type_id = dt.id
        LEFT JOIN provinces p ON l.province_id = p.province_id
        LEFT JOIN districts d ON l.district_id = d.district_id
        JOIN assignments a ON a.request_id = hr.id
        WHERE a.volunteer_id = ? AND a.accepted = 1
        ORDER BY hr.created_at DESC
    """,
        (session["user_id"],),
    )
    accepted_requests = c.fetchall()

    conn.close()
    return render_template(
        "volunteer_panel.html",
        pending_requests=pending_requests,
        accepted_requests=accepted_requests,
        volunteer_location={"latitude": volunteer_lat, "longitude": volunteer_lon},
    )


@app.route("/koordinator-panel", methods=["GET", "POST"])
def coordinator_panel():
    if session.get("role") != "coordinator":
        return redirect(url_for("sign_in"))

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        request_id = request.form.get("request_id")
        new_status = request.form.get("status")
        volunteer_ids = request.form.getlist("volunteer_ids[]")

        try:
            if request_id and new_status:
                # Yardım talebi durumunu güncelle
                c.execute(
                    "UPDATE help_requests SET status = ? WHERE id = ?",
                    (new_status, request_id),
                )

                # Seçilen gönüllüleri ata
                if volunteer_ids:
                    # Önce mevcut atamaları temizle
                    c.execute(
                        "DELETE FROM assignments WHERE request_id = ?", (request_id,)
                    )

                    # Yeni atamaları ekle (accepted=0, gönüllü onaylamalı)
                    for volunteer_id in volunteer_ids:
                        c.execute(
                            """
                            INSERT INTO assignments (request_id, volunteer_id, accepted)
                            VALUES (?, ?, 0)
                        """,
                            (request_id, volunteer_id),
                        )

                conn.commit()
                flash("Yardım talebi başarıyla güncellendi.", "success")
            else:
                flash("Geçersiz form verisi.", "error")
        except sqlite3.Error as e:
            conn.rollback()
            flash("Güncelleme sırasında bir hata oluştu.", "error")

        return redirect(url_for("coordinator_panel"))

    # Tüm yardım taleplerini al
    c.execute(
        """
        SELECT 
            hr.id,
            hr.status,
            hr.created_at,
            hr.additional_info,
            dt.name as disaster_type,
            l.latitude,
            l.longitude,
            u.fullname as requester_name,
            (SELECT COUNT(*) FROM assignments a WHERE a.request_id = hr.id) as volunteer_count,
            GROUP_CONCAT(a.volunteer_id) as assigned_volunteers
        FROM help_requests hr
        LEFT JOIN disasters d ON d.location_id = hr.location_id
        LEFT JOIN disaster_types dt ON d.disaster_type_id = dt.id
        LEFT JOIN locations l ON hr.location_id = l.id
        LEFT JOIN users u ON hr.requester_id = u.id
        LEFT JOIN assignments a ON hr.id = a.request_id
        GROUP BY hr.id
        ORDER BY hr.created_at DESC
    """
    )
    help_requests = c.fetchall()

    # Atanan gönüllüleri işle
    processed_requests = []
    for req in help_requests:
        req_dict = dict(req)
        # assigned_volunteers string'ini liste haline getir
        if req_dict["assigned_volunteers"]:
            req_dict["assigned_volunteers"] = [
                int(v) for v in req_dict["assigned_volunteers"].split(",")
            ]
        else:
            req_dict["assigned_volunteers"] = []
        processed_requests.append(req_dict)

    # --- Gönüllülerin başka bir görevi kabul edip etmediğini bulmak için ---
    c.execute(
        """
        SELECT a.volunteer_id
        FROM assignments a
        WHERE a.accepted = 1
    """
    )
    busy_volunteers = set(row[0] for row in c.fetchall())

    # Aktif gönüllüleri ve istatistiklerini al
    c.execute(
        """
        SELECT 
            u.id, 
            u.fullname, 
            u.phone, 
            u.email,
            (SELECT COUNT(*) FROM assignments a 
             WHERE a.volunteer_id = u.id AND a.completed_at IS NOT NULL) as completed_tasks,
            (SELECT COUNT(*) FROM assignments a 
             WHERE a.volunteer_id = u.id AND a.completed_at IS NULL) as active_tasks,
            l.latitude,
            l.longitude
        FROM users u
        JOIN roles r ON u.role_id = r.id
        LEFT JOIN volunteer_details vd ON u.id = vd.user_id
        LEFT JOIN locations l ON vd.location_id = l.id
        WHERE r.name = 'volunteer' AND u.is_active = 1
    """
    )
    all_volunteers = c.fetchall()
    # Sadece başka bir görevi kabul etmemiş olanlar
    volunteers_row = [v for v in all_volunteers if v[0] not in busy_volunteers]
    volunteers_json = [dict(v) for v in volunteers_row]

    conn.close()
    # Benzersiz afet türleri
    disaster_types = list(
        {req["disaster_type"] for req in processed_requests if req["disaster_type"]}
    )
    disaster_types.sort()

    return render_template(
        "coordinator_panel.html",
        help_requests=processed_requests,
        volunteers=volunteers_row,  # HTML döngüsü için
        volunteers_json=volunteers_json,  # JS için
        disaster_types=disaster_types,
    )


@app.route("/requester-panel", methods=["GET", "POST"])
def requester_panel():
    if session.get("role") != "requester":
        return redirect(url_for("sign_in"))

    conn = get_db()
    c = conn.cursor()

    # Kullanıcının yardım taleplerini al
    c.execute(
        """
        SELECT hr.id, hr.status, hr.created_at, hr.additional_info,
               dt.name as disaster_type,
               l.latitude, l.longitude,
               (SELECT COUNT(*) FROM assignments a WHERE a.request_id = hr.id) as volunteer_count
        FROM help_requests hr
        JOIN disasters d ON d.location_id = hr.location_id
        JOIN disaster_types dt ON d.disaster_type_id = dt.id
        JOIN locations l ON hr.location_id = l.id
        WHERE hr.requester_id = ?
        ORDER BY hr.created_at DESC
    """,
        (session["user_id"],),
    )
    help_requests = c.fetchall()

    conn.close()
    return render_template("requester_panel.html", help_requests=help_requests)


def get_current_user():
    user_id = session.get("user_id")
    role = session.get("role")
    if user_id and role:
        return {"is_authenticated": True, "role": role}
    return {"is_authenticated": False, "role": None}


@app.context_processor
def inject_user():
    return dict(current_user=get_current_user())


def init_db():
    conn = get_db()
    c = conn.cursor()
    try:
        # Tablo oluşturma komutlarını harici dosyadan oku
        with open("schema.sql", "r", encoding="utf-8") as f:
            schema_sql = f.read()
        c.executescript(schema_sql)
        conn.commit()
        conn.close()
        print("Veritabanı tabloları başarıyla oluşturuldu.")
    except sqlite3.Error as e:
        print(f"Veritabanı oluşturulurken hata oluştu: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        raise e


def insert_address_db():
    # tr_adres_sqlite.sql dosyasını çalıştır
    try:
        conn = get_db()
        c = conn.cursor()
        with open("tr_adres_sqlite.sql", "r", encoding="utf-8") as f:
            sql_script = f.read()
        c.executescript(sql_script)
        conn.commit()
        print("Adres veritabanı başarıyla eklendi.")
    except sqlite3.Error as e:
        print(f"Adres veritabanı eklenirken hata oluştu: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        raise e


def insert_initial_data():
    conn = get_db()
    c = conn.cursor()

    # 1. Insert roles
    c.executemany(
        "INSERT OR IGNORE INTO roles (name) VALUES (?)",
        [("volunteer",), ("requester",), ("coordinator",), ("admin",)],
    )

    # 2. Insert disaster types
    c.executemany(
        "INSERT OR IGNORE INTO disaster_types (name) VALUES (?)",
        [("Deprem",), ("Sel",), ("Yangın",), ("Heyelan",), ("Çığ",), ("Diğer",)],
    )

    # 3. Insert locations across Turkey - Gerçek şehir verileri
    locations = [
        (34, 1, 1, 1, 41.0082, 28.9784),  # İstanbul
        (16, 1, 1, 1, 40.1885, 29.0610),  # Bursa
        (41, 1, 1, 1, 40.7655, 29.9408),  # Kocaeli
        (35, 1, 1, 1, 38.4192, 27.1287),  # İzmir
        (45, 1, 1, 1, 38.6191, 27.4289),  # Manisa
        (17, 1, 1, 1, 40.1553, 26.4142),  # Çanakkale
        (7, 1, 1, 1, 36.8841, 30.7056),  # Antalya
        (1, 1, 1, 1, 37.0000, 35.3213),  # Adana
        (32, 1, 1, 1, 37.7648, 30.5566),  # Isparta
        (6, 1, 1, 1, 39.9334, 32.8597),  # Ankara
        (42, 1, 1, 1, 37.8667, 32.4833),  # Konya
        (26, 1, 1, 1, 39.7767, 30.5206),  # Eskişehir
        (55, 1, 1, 1, 41.2867, 36.3300),  # Samsun
        (28, 1, 1, 1, 40.9128, 38.3895),  # Giresun
        (19, 1, 1, 1, 40.5506, 34.9556),  # Çorum
        (25, 1, 1, 1, 39.9208, 41.2675),  # Erzurum
        (65, 1, 1, 1, 38.4891, 43.4089),  # Van
        (4, 1, 1, 1, 39.7191, 43.0503),  # Ağrı
        (21, 1, 1, 1, 37.9144, 40.2306),  # Diyarbakır
        (46, 1, 1, 1, 37.5858, 36.9371),  # Kahramanmaraş
        (72, 1, 1, 1, 37.8812, 41.1351),  # Batman
    ]

    c.executemany(
        "INSERT OR IGNORE INTO locations (province_id, district_id, neighborhood_id, street_id, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)",
        [(loc[0], loc[1], loc[2], loc[3], loc[4], loc[5]) for loc in locations],
    )

    # 4. Create test admin account
    c.execute("SELECT id FROM users WHERE email = 'admin@test.com'")
    if not c.fetchone():
        c.execute(
            """
            INSERT OR IGNORE INTO users (fullname, username, email, password_hash, role_id)
            SELECT 'Test Admin', 'admin', 'admin@test.com', ?, r.id 
            FROM roles r WHERE r.name = 'admin'
            """,
            (generate_password_hash("test123"),),
        )

    # 5. Create test coordinator account
    c.execute("SELECT id FROM users WHERE email = 'mehmet.ozkan@afetkoord.org'")
    if not c.fetchone():
        c.execute(
            """
            INSERT OR IGNORE INTO users (fullname, username, email, phone, password_hash, role_id)
            SELECT 'Mehmet Özkan', 'coordinator', 'mehmet.ozkan@afetkoord.org', '05321234567', ?, r.id
            FROM roles r WHERE r.name = 'coordinator'
            """,
            (generate_password_hash("test123"),),
        )

    # 6. Create test volunteers with different locations
    volunteer_data = [
        (
            "Ayşe Demir",
            "aysedemir",
            "ayse.demir@gmail.com",
            "05339876543",
            "Arama Kurtarma",
            "İlk Yardım Sertifikası, UMKE Eğitimi",
            "10 yıllık arama kurtarma deneyimi. Dağcılık ve su altı kurtarma konularında uzman.",
            0,
        ),  # İstanbul
        (
            "Can Yılmaz",
            "canyilmaz",
            "can.yilmaz@hotmail.com",
            "05425678901",
            "Lojistik",
            "Forklift Ehliyeti, Lojistik Yönetimi Sertifikası",
            "Lojistik sektöründe 8 yıl deneyim. Afet durumlarında malzeme koordinasyonu yapabilirim.",
            3,
        ),  # İzmir
        (
            "Dr. Zeynep Kaya",
            "zeynepkaya",
            "dr.zeynep.kaya@yahoo.com",
            "05567890123",
            "Sağlık",
            "Tıp Doktoru, Acil Tıp Uzmanı",
            "Acil tıp uzmanıyım. Afet bölgelerinde tıbbi müdahale ve triage konusunda deneyimliyim.",
            6,
        ),  # Antalya
        (
            "Psikolog Emre Şahin",
            "emresahin",
            "emre.sahin@outlook.com",
            "05478901234",
            "Psikososyal",
            "Klinik Psikolog, Travma Sonrası Stres Bozukluğu Uzmanı",
            "Afet mağdurlarına psikososyal destek sağlama konusunda 6 yıl deneyimim var.",
            9,
        ),  # Ankara
        (
            "Fatma Koç",
            "fatmakoc",
            "fatma.koc@gmail.com",
            "05389012345",
            "Arama Kurtarma",
            "AKUT Gönüllüsü, Yüksek İrtifa Eğitimi",
            "AKUT'ta 12 yıldır gönüllüyüm. Dağ kurtarma ve çığ arama operasyonlarında deneyimliyim.",
            12,
        ),  # Samsun
        (
            "Murat Aksoy",
            "murataksoy",
            "murat.aksoy@hotmail.com",
            "05490123456",
            "Lojistik",
            "Kargo ve Nakliye Sertifikası, İş Makinesi Operatörü",
            "İnşaat sektöründe çalışıyorum. Ağır makine operatörüyüm ve enkaz kaldırma işlerinde yardımcı olabilirim.",
            15,
        ),  # Erzurum
        (
            "Hemşire Elif Bulut",
            "elifbulut",
            "elif.bulut@yahoo.com",
            "05401234567",
            "Sağlık",
            "Hemşire, Yoğun Bakım Sertifikası",
            "Yoğun bakım hemşiresiyim. Acil durumlarda hasta bakımı ve tıbbi destek sağlayabilirim.",
            18,
        ),  # Diyarbakır
    ]

    for (
        fullname,
        username,
        email,
        phone,
        expertise,
        certifications,
        additional_info,
        loc_idx,
    ) in volunteer_data:
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        if not c.fetchone():
            c.execute(
                """
                INSERT OR IGNORE INTO users (fullname, username, email, phone, password_hash, role_id)
                SELECT ?, ?, ?, ?, ?, r.id FROM roles r WHERE r.name = 'volunteer'
                """,
                (fullname, username, email, phone, generate_password_hash("test123")),
            )
            c.execute("SELECT id FROM users WHERE email = ?", (email,))
            user_id = c.fetchone()[0]
            c.execute("SELECT id FROM locations LIMIT 1 OFFSET ?", (loc_idx,))
            location_id = c.fetchone()[0]
            c.execute(
                """
                INSERT OR IGNORE INTO volunteer_details (user_id, location_id, expertise, certifications, additional_info)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, location_id, expertise, certifications, additional_info),
            )

    # 7. Create test requesters
    requester_data = [
        (
            "Ahmet Yıldırım",
            "ahmetyildirim",
            "ahmet.yildirim@gmail.com",
            "05356789012",
            "Eşi: Hacer Yıldırım - 05367890123",
            "Diyabet, Kalp rahatsızlığı",
            "65 yaşındayım. Evim depremde hasar gördü. Geçici barınma yeri ve ilaç temin etme konusunda yardıma ihtiyacım var.",
        ),
        (
            "Sevim Özdemir",
            "sevimozdemir",
            "sevim.ozdemir@hotmail.com",
            "05445678123",
            "Oğlu: Hasan Özdemir - 05456781234",
            "Astım, Hipertansiyon",
            "Sel felaketi sonrası evim kullanılamaz halde. 2 yaşında torunum var. Güvenli barınma ve bebek maması ihtiyacımız var.",
        ),
        (
            "Mustafa Çelik",
            "mustafacelik",
            "mustafa.celik@yahoo.com",
            "05523456789",
            "Eşi: Ayten Çelik - 05534567890",
            "Yok",
            "Yangın sonrası ev eşyalarımızın tamamını kaybettik. 3 çocuğum var. Giyecek ve temel ihtiyaç malzemelerine acil ihtiyacımız var.",
        ),
    ]

    for (
        fullname,
        username,
        email,
        phone,
        emergency_contact,
        medical_conditions,
        additional_info,
    ) in requester_data:
        c.execute("SELECT id FROM users WHERE email = ?", (email,))
        if not c.fetchone():
            c.execute(
                """
                INSERT OR IGNORE INTO users (fullname, username, email, phone, password_hash, role_id)
                SELECT ?, ?, ?, ?, ?, r.id FROM roles r WHERE r.name = 'requester'
                """,
                (fullname, username, email, phone, generate_password_hash("test123")),
            )
            c.execute("SELECT id FROM users WHERE email = ?", (email,))
            user_id = c.fetchone()[0]
            c.execute(
                """
                INSERT OR IGNORE INTO requester_details (user_id, emergency_contact, medical_conditions, additional_info)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, emergency_contact, medical_conditions, additional_info),
            )

    # 8. Create sample disasters and help requests with realistic data
    c.execute("SELECT id FROM disaster_types")
    disaster_type_ids = [row[0] for row in c.fetchall()]
    c.execute("SELECT id FROM locations")
    location_ids = [row[0] for row in c.fetchall()]
    c.execute(
        "SELECT id FROM users WHERE role_id = (SELECT id FROM roles WHERE name = 'requester')"
    )
    requester_ids = [row[0] for row in c.fetchall()]

    import random

    # Gerçekçi yardım talepleri
    realistic_requests = [
        "Deprem sonrası evimiz kullanılamaz halde. Acil barınma yeri ihtiyacımız var.",
        "Sel sularına kapılan eşyalarımızı kaybettik. Giyecek ve battaniye ihtiyacımız var.",
        "Yaşlı annem için ilaç temin etmemiz gerekiyor. Eczaneler kapalı.",
        "Çocuklarım için bebek maması ve bez ihtiyacımız var acil olarak.",
        "Evimizin çatısı yangında zarar gördü. Geçici onarım yapılması gerekiyor.",
        "Su ve gıda sıkıntımız var. Temel ihtiyaç malzemelerine ihtiyacımız var.",
        "Depremden sonra psikolojik destek ihtiyacımız var. Çocuklarım çok korkuyor.",
        "Evimizin elektrik tesisatı hasarlı. Elektrikçi yardımına ihtiyacımız var.",
        "Yaralı komşumuz var, hastaneye ulaştırılması gerekiyor.",
        "Enkaz altında kalan eşyalarımızı çıkarabilmek için yardıma ihtiyacımız var.",
    ]

    for i in range(10):
        requester_id = random.choice(requester_ids)
        disaster_type_id = random.choice(disaster_type_ids)
        location_id = random.choice(location_ids)
        additional_info = realistic_requests[i]

        # Disaster kaydı
        c.execute(
            "INSERT INTO disasters (disaster_type_id, location_id, description, started_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (disaster_type_id, location_id, additional_info),
        )

        # Help request kaydı
        c.execute(
            "INSERT INTO help_requests (requester_id, location_id, additional_info, status) VALUES (?, ?, ?, 'pending')",
            (requester_id, location_id, additional_info),
        )

    conn.commit()
    conn.close()


@app.route("/logout")
def logout():
    # Session'daki tüm verileri temizle
    session.clear()
    # Kullanıcıyı ana sayfaya yönlendir
    flash("Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for("index"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not session.get("user_id"):
        return redirect(url_for("sign_in"))

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "request_coordinator":
            # Koordinatör olma isteği gönderme
            if session.get("role") != "volunteer":
                flash(
                    "Sadece gönüllüler koordinatör olma isteği gönderebilir.", "error"
                )
                return redirect(url_for("profile"))

            request_reason = request.form.get("request_reason", "").strip()

            if not request_reason:
                flash("Lütfen koordinatör olmak isteme nedeninizi belirtin.", "error")
                return redirect(url_for("profile"))

            # Daha önce beklemede olan bir istek var mı kontrol et
            c.execute(
                "SELECT id FROM coordinator_requests WHERE user_id = ? AND status = 'pending'",
                (session["user_id"],),
            )
            existing_request = c.fetchone()

            if existing_request:
                flash(
                    "Zaten beklemede olan bir koordinatör başvurunuz bulunmaktadır.",
                    "warning",
                )
                return redirect(url_for("profile"))

            # Yeni istek oluştur
            try:
                c.execute(
                    """
                    INSERT INTO coordinator_requests (user_id, request_reason, status)
                    VALUES (?, ?, 'pending')
                    """,
                    (session["user_id"], request_reason),
                )
                conn.commit()
                flash(
                    "Koordinatör başvurunuz başarıyla gönderildi. İnceleme sürecinde bilgilendirileceksiniz.",
                    "success",
                )
            except sqlite3.Error as e:
                conn.rollback()
                flash("Başvuru gönderilirken bir hata oluştu.", "error")

            return redirect(url_for("profile"))

    # Kullanıcı bilgilerini al
    c.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    user = c.fetchone()

    # Kullanıcının yardım taleplerini al
    c.execute(
        """
        SELECT hr.*, dt.name as disaster_type, l.latitude, l.longitude
        FROM help_requests hr
        LEFT JOIN disasters d ON d.location_id = hr.location_id
        LEFT JOIN disaster_types dt ON d.disaster_type_id = dt.id
        LEFT JOIN locations l ON hr.location_id = l.id
        WHERE hr.requester_id = ?
        ORDER BY hr.created_at DESC
    """,
        (session["user_id"],),
    )
    help_requests = c.fetchall()

    # Gönüllü ise katıldığı yardımları al
    if session["role"] == "volunteer":
        c.execute(
            """
            SELECT hr.*, dt.name as disaster_type, l.latitude, l.longitude
            FROM help_requests hr
            JOIN assignments a ON hr.id = a.request_id
            JOIN disasters d ON d.location_id = hr.location_id
            JOIN disaster_types dt ON d.disaster_type_id = dt.id
            JOIN locations l ON hr.location_id = l.id
            WHERE a.volunteer_id = ?
            ORDER BY hr.created_at DESC
        """,
            (session["user_id"],),
        )
        volunteer_help_requests = c.fetchall()

        # Koordinatör başvuru durumunu kontrol et
        c.execute(
            """
            SELECT status, request_reason FROM coordinator_requests 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            (session["user_id"],),
        )
        coordinator_request = c.fetchone()
        coordinator_request_status = (
            coordinator_request[0] if coordinator_request else None
        )
        coordinator_request_reason = (
            coordinator_request[1] if coordinator_request else None
        )
    else:
        volunteer_help_requests = []
        coordinator_request_status = None
        coordinator_request_reason = None

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        help_requests=help_requests,
        volunteer_help_requests=volunteer_help_requests,
        coordinator_request_status=coordinator_request_status,
        coordinator_request_reason=coordinator_request_reason,
    )
    if not session.get("user_id"):
        return redirect(url_for("sign_in"))

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "request_coordinator":
            # Koordinatör olma isteği gönderme
            if session.get("role") != "volunteer":
                flash(
                    "Sadece gönüllüler koordinatör olma isteği gönderebilir.", "error"
                )
                return redirect(url_for("profile"))

            request_reason = request.form.get("request_reason", "").strip()

            if not request_reason:
                flash("Lütfen koordinatör olmak isteme nedeninizi belirtin.", "error")
                return redirect(url_for("profile"))

            # Daha önce beklemede olan bir istek var mı kontrol et
            c.execute(
                "SELECT id FROM coordinator_requests WHERE user_id = ? AND status = 'pending'",
                (session["user_id"],),
            )
            existing_request = c.fetchone()

            if existing_request:
                flash(
                    "Zaten beklemede olan bir koordinatör başvurunuz bulunmaktadır.",
                    "warning",
                )
                return redirect(url_for("profile"))

            # Yeni istek oluştur
            try:
                c.execute(
                    """
                    INSERT INTO coordinator_requests (user_id, request_reason, status)
                    VALUES (?, ?, 'pending')
                    """,
                    (session["user_id"], request_reason),
                )
                conn.commit()
                flash(
                    "Koordinatör başvurunuz başarıyla gönderildi. İnceleme sürecinde bilgilendirileceksiniz.",
                    "success",
                )
            except sqlite3.Error as e:
                conn.rollback()
                flash("Başvuru gönderilirken bir hata oluştu.", "error")

            return redirect(url_for("profile"))

    # Kullanıcı bilgilerini al
    c.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    user = c.fetchone()

    # Kullanıcının yardım taleplerini al
    c.execute(
        """
        SELECT hr.*, dt.name as disaster_type, l.latitude, l.longitude
        FROM help_requests hr
        LEFT JOIN disasters d ON d.location_id = hr.location_id
        LEFT JOIN disaster_types dt ON d.disaster_type_id = dt.id
        LEFT JOIN locations l ON hr.location_id = l.id
        WHERE hr.requester_id = ?
        ORDER BY hr.created_at DESC
    """,
        (session["user_id"],),
    )
    help_requests = c.fetchall()

    # Gönüllü ise katıldığı yardımları al
    if session["role"] == "volunteer":
        c.execute(
            """
            SELECT hr.*, dt.name as disaster_type, l.latitude, l.longitude
            FROM help_requests hr
            JOIN assignments a ON hr.id = a.request_id
            JOIN disasters d ON d.location_id = hr.location_id
            JOIN disaster_types dt ON d.disaster_type_id = dt.id
            JOIN locations l ON hr.location_id = l.id
            WHERE a.volunteer_id = ?
            ORDER BY hr.created_at DESC
        """,
            (session["user_id"],),
        )
        volunteer_help_requests = c.fetchall()

        # Koordinatör başvuru durumunu kontrol et
        c.execute(
            """
            SELECT status, request_reason FROM coordinator_requests 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            (session["user_id"],),
        )
        coordinator_request = c.fetchone()
        coordinator_request_status = (
            coordinator_request[0] if coordinator_request else None
        )
        coordinator_request_reason = (
            coordinator_request[1] if coordinator_request else None
        )
    else:
        volunteer_help_requests = []
        coordinator_request_status = None
        coordinator_request_reason = None

    conn.close()

    return render_template(
        "profile.html",
        user=user,
        help_requests=help_requests,
        volunteer_help_requests=volunteer_help_requests,
        coordinator_request_status=coordinator_request_status,
        coordinator_request_reason=coordinator_request_reason,
    )


def validate_profile_form(form, c, user_id):
    errors = []
    fullname = form.get("fullname", "").strip()
    username = form.get("username", "").strip()
    email = form.get("email", "").strip()
    current_password = form.get("current_password", "").strip()
    new_password = form.get("new_password", "").strip()
    phone = form.get("phone", "").strip()

    # Ad Soyad doğrulama
    if not fullname:
        errors.append("Ad Soyad alanı zorunludur.")
    elif len(fullname) < 3 or len(fullname) > 50:
        errors.append("Ad Soyad 3-50 karakter arasında olmalıdır.")
    elif not re.match(r"^[A-Za-zğüşıöçĞÜŞİÖÇ0-9\s]+$", fullname):
        errors.append("Ad Soyad sadece harfler, rakamlar ve boşluk içerebilir.")

    # Kullanıcı adı doğrulama
    if not username:
        errors.append("Kullanıcı adı alanı zorunludur.")
    elif len(username) < 3 or len(username) > 20:
        errors.append("Kullanıcı adı 3-20 karakter arasında olmalıdır.")
    elif not re.match(r"^\w+$", username):
        errors.append(
            "Kullanıcı adı sadece harfler, rakamlar ve alt çizgi (_) içerebilir."
        )

    # E-posta doğrulama
    if not email:
        errors.append("E-posta adresi alanı zorunludur.")
    elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        errors.append("Geçerli bir e-posta adresi giriniz.")

    # Telefon doğrulama (opsiyonel)
    if phone:
        cleaned_phone = re.sub(r"[\s\-\(\)]+", "", phone)
        if not re.match(r"^\+?\d{10,15}$", cleaned_phone):
            errors.append(
                "Geçerli bir telefon numarası giriniz (örn: +90 5XX XXX XX XX)."
            )

    # Şifre değişikliği doğrulama
    if new_password:
        if len(new_password) < 4:
            errors.append("Yeni şifre en az 4 karakter uzunluğunda olmalıdır.")
        if not current_password:
            errors.append("Şifre değiştirmek için mevcut şifrenizi girmelisiniz.")
        else:
            c.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
            user = c.fetchone()
            if user and not check_password_hash(
                user["password_hash"], current_password
            ):
                errors.append("Mevcut şifreniz yanlış.")

    # Kullanıcı adı benzersizliği
    c.execute(
        "SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id)
    )
    if c.fetchone():
        errors.append("Bu kullanıcı adı zaten kullanılıyor.")

    # E-posta benzersizliği
    c.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id))
    if c.fetchone():
        errors.append("Bu e-posta adresi zaten kullanılıyor.")

    return errors


def get_user_data(c, user_id):
    c.execute(
        """
        SELECT u.fullname, u.phone, u.username, u.email 
        FROM users u
        WHERE u.id = ?
        """,
        (user_id,),
    )
    return c.fetchone()


def update_user_data(c, user_id, fullname, phone, username, email, new_password=None):
    if new_password:
        c.execute(
            """
            UPDATE users 
            SET fullname = ?, phone = ?, username = ?, email = ?, password_hash = ?
            WHERE id = ?
            """,
            (
                fullname,
                phone,
                username,
                email,
                generate_password_hash(new_password),
                user_id,
            ),
        )
    else:
        c.execute(
            """
            UPDATE users 
            SET fullname = ?, phone = ?, username = ?, email = ?
            WHERE id = ?
            """,
            (fullname, phone, username, email, user_id),
        )


@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    if not session.get("user_id"):
        return redirect(url_for("sign_in"))

    conn = get_db()
    c = conn.cursor()
    user_id = session["user_id"]

    try:
        if request.method == "POST":
            form = request.form
            fullname = form.get("fullname", "").strip()
            username = form.get("username", "").strip()
            email = form.get("email", "").strip()
            phone = form.get("phone", "").strip()
            new_password = form.get("new_password", "").strip()

            errors = validate_profile_form(form, c, user_id)

            if errors:
                for error in errors:
                    flash(error, "error")
                current_user = get_user_data(c, user_id)
                user_data = {
                    "fullname": fullname
                    or (current_user["fullname"] if current_user else ""),
                    "username": username
                    or (current_user["username"] if current_user else ""),
                    "email": email or (current_user["email"] if current_user else ""),
                    "phone": phone or (current_user["phone"] if current_user else ""),
                }
                return render_template("edit_profile.html", user=user_data)

            update_user_data(
                c,
                user_id,
                fullname,
                phone,
                username,
                email,
                new_password if new_password else None,
            )
            conn.commit()
            flash("Profil bilgileriniz başarıyla güncellendi.", "success")
            return redirect(url_for("profile"))

        # GET isteği için kullanıcı bilgilerini al
        user = get_user_data(c, user_id)
        if user:
            return render_template("edit_profile.html", user=user)
        else:
            flash("Kullanıcı bulunamadı.", "error")
            return redirect(url_for("profile"))

    except sqlite3.Error as e:
        flash(
            "Profil güncellenirken bir veritabanı hatası oluştu. Lütfen daha sonra tekrar deneyin.",
            "error",
        )
        print(f"Database error in edit_profile: {str(e)}")
        return redirect(url_for("profile"))
    except Exception as e:
        flash(
            "Profil güncellenirken beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
            "error",
        )
        print(f"Unexpected error in edit_profile: {str(e)}")
        return redirect(url_for("profile"))
    finally:
        if "conn" in locals():
            conn.close()


@app.route("/api/streets/<int:neighborhood_id>")
def get_streets(neighborhood_id):
    conn = get_db()
    c = conn.cursor()

    # Sadece gerekli alanları seç ve indeks kullan
    c.execute(
        """
        SELECT street_id, street_name 
        FROM streets 
        WHERE neighborhood_id = ? 
        ORDER BY street_name COLLATE NOCASE
    """,
        (neighborhood_id,),
    )

    streets = [{"street_id": row[0], "street_name": row[1]} for row in c.fetchall()]
    conn.close()

    return jsonify(streets)


@app.route("/admin-panel", methods=["GET", "POST"])
def admin_panel():
    if session.get("role") != "admin":
        flash("Bu sayfaya erişim yetkiniz bulunmamaktadır.", "error")
        return redirect(url_for("sign_in"))

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")
        request_id = request.form.get("request_id")
        user_id = request.form.get("user_id")
        admin_notes = request.form.get("admin_notes", "")

        try:
            if action == "approve_coordinator" and request_id:
                # Koordinatör isteğini onayla
                c.execute(
                    """
                    UPDATE coordinator_requests 
                    SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP, 
                        reviewed_by = ?, admin_notes = ?
                    WHERE id = ?
                    """,
                    (session["user_id"], admin_notes, request_id),
                )

                # Kullanıcının rolünü koordinatör yap
                c.execute(
                    """
                    SELECT user_id FROM coordinator_requests WHERE id = ?
                    """,
                    (request_id,),
                )
                user_result = c.fetchone()

                if user_result:
                    user_id = user_result[0]
                    c.execute(
                        """
                        UPDATE users 
                        SET role_id = (SELECT id FROM roles WHERE name = 'coordinator')
                        WHERE id = ?
                        """,
                        (user_id,),
                    )
                    flash(
                        "Koordinatör isteği onaylandı ve kullanıcı rolü güncellendi.",
                        "success",
                    )

            elif action == "reject_coordinator" and request_id:
                # Koordinatör isteğini reddet
                c.execute(
                    """
                    UPDATE coordinator_requests 
                    SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP, 
                        reviewed_by = ?, admin_notes = ?
                    WHERE id = ?
                    """,
                    (session["user_id"], admin_notes, request_id),
                )
                flash("Koordinatör isteği reddedildi.", "info")

            elif action == "block_user" and user_id:
                # Kullanıcıyı engelle
                c.execute(
                    """
                    UPDATE users SET is_blocked = 1 WHERE id = ?
                    """,
                    (user_id,),
                )
                flash("Kullanıcı başarıyla engellendi.", "success")

            elif action == "unblock_user" and user_id:
                # Kullanıcının engelini kaldır
                c.execute(
                    """
                    UPDATE users SET is_blocked = 0 WHERE id = ?
                    """,
                    (user_id,),
                )
                flash("Kullanıcının engeli başarıyla kaldırıldı.", "success")

            elif action == "promote_to_coordinator" and user_id:
                # Gönüllüyü koordinatör yap
                c.execute(
                    """
                    UPDATE users 
                    SET role_id = (SELECT id FROM roles WHERE name = 'coordinator')
                    WHERE id = ?
                    """,
                    (user_id,),
                )
                flash("Kullanıcı başarıyla koordinatör yapıldı.", "success")

            elif action == "revoke_coordinator" and request_id:
                # Koordinatör onayını geri çek
                c.execute(
                    """
                    UPDATE coordinator_requests 
                    SET status = 'revoked', reviewed_at = CURRENT_TIMESTAMP, 
                        reviewed_by = ?, admin_notes = ?
                    WHERE id = ?
                    """,
                    (session["user_id"], admin_notes, request_id),
                )

                # Kullanıcının rolünü tekrar gönüllü yap
                c.execute(
                    """
                    SELECT user_id FROM coordinator_requests WHERE id = ?
                    """,
                    (request_id,),
                )
                user_result = c.fetchone()

                if user_result:
                    user_id = user_result[0]
                    c.execute(
                        """
                        UPDATE users 
                        SET role_id = (SELECT id FROM roles WHERE name = 'volunteer')
                        WHERE id = ?
                        """,
                        (user_id,),
                    )
                    flash(
                        "Koordinatör onayı geri çekildi ve kullanıcı rolü gönüllü olarak güncellendi.",
                        "success",
                    )

            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            flash("İşlem sırasında bir hata oluştu.", "error")
            print(f"Admin panel error: {e}")

        return redirect(url_for("admin_panel"))

    # İstatistikleri al
    c.execute(
        "SELECT COUNT(*) FROM users WHERE role_id = (SELECT id FROM roles WHERE name = 'volunteer')"
    )
    volunteer_count = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM users WHERE role_id = (SELECT id FROM roles WHERE name = 'coordinator')"
    )
    coordinator_count = c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM users WHERE role_id = (SELECT id FROM roles WHERE name = 'requester')"
    )
    requester_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM coordinator_requests WHERE status = 'pending'")
    pending_requests_count = c.fetchone()[0]

    # Tüm koordinatör isteklerini al (pending, approved, rejected)
    c.execute(
        """
        SELECT cr.id, cr.user_id, cr.request_reason, cr.created_at, cr.status,
               cr.reviewed_at, cr.admin_notes,
               u.fullname, u.username, u.email, u.phone
        FROM coordinator_requests cr
        JOIN users u ON cr.user_id = u.id
        ORDER BY cr.created_at DESC
        """
    )
    coordinator_requests = c.fetchall()

    # Tüm kullanıcıları al (admin hariç)
    c.execute(
        """
        SELECT u.id, u.fullname, u.username, u.email, u.phone, u.created_at, 
               u.last_login, u.is_blocked, r.name as role_name
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE r.name != 'admin'
        ORDER BY u.created_at DESC
        """
    )
    users = c.fetchall()

    conn.close()

    return render_template(
        "admin_panel.html",
        volunteer_count=volunteer_count,
        coordinator_count=coordinator_count,
        requester_count=requester_count,
        pending_requests_count=pending_requests_count,
        coordinator_requests=coordinator_requests,
        users=users,
    )


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print("Initializing database...")
        init_db()
        print("Inserting initial data...")
        insert_initial_data()
        print("Inserting address data...")
        insert_address_db()
    app.run(debug=True)


# --- Templates (templates/ folder) ---
# index.html, help.html, help_sended.html,
# sign_up.html, sign_in.html, 
# profile.html, edit_profile.html, 
# requester_panel.html, volunteer_panel.html, coordinator_panel.html,
# admin_panel.html, 
