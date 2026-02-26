from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)
DATABASE = "parking.db"


# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parking_slots (
        slotNo INTEGER PRIMARY KEY,
        isCovered BOOLEAN NOT NULL,
        isEVCharging BOOLEAN NOT NULL,
        isOccupied BOOLEAN NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


init_db()


# ---------------- HOME ----------------
@app.route("/")
def index():
    conn = get_db_connection()
    slots = conn.execute("SELECT * FROM parking_slots ORDER BY slotNo ASC").fetchall()
    conn.close()
    return render_template("index.html", slots=slots)


# ---------------- ADD SLOT ----------------
@app.route("/add", methods=["GET", "POST"])
def add_slot():
    message = ""
    message_type = ""

    if request.method == "POST":
        try:
            slot_no = int(request.form["slotNo"])

            if slot_no <= 0:
                message = "Slot number must be positive."
                message_type = "error"
                return render_template("add_slot.html", message=message)

            is_covered = 1 if request.form.get("isCovered") == "on" else 0
            is_ev = 1 if request.form.get("isEVCharging") == "on" else 0

            conn = get_db_connection()
            cursor = conn.cursor()

            # Check duplicate slot
            existing = cursor.execute(
                "SELECT * FROM parking_slots WHERE slotNo = ?",
                (slot_no,)
            ).fetchone()

            if existing:
                message = "Slot added successfully."
                message_type = "success"
            else:
                cursor.execute("""
                    INSERT INTO parking_slots (slotNo, isCovered, isEVCharging, isOccupied)
                    VALUES (?, ?, ?, 0)
                """, (slot_no, is_covered, is_ev))
                conn.commit()
                message = "Slot added successfully."

            conn.close()

        except ValueError:
            message = "Invalid slot number."

    return render_template("add_slot.html", message=message, message_type=message_type)


# ---------------- PARK VEHICLE ----------------
@app.route("/park", methods=["GET", "POST"])
def park():
    message = ""
    message_type = ""
    if request.method == "POST":
        needs_ev = 1 if request.form.get("needsEV") == "on" else 0
        needs_cover = 1 if request.form.get("needsCover") == "on" else 0

        conn = get_db_connection()
        cursor = conn.cursor()

        # Optimized allocation query
        slot = cursor.execute("""
            SELECT * FROM parking_slots
            WHERE isOccupied = 0
            AND isEVCharging >= ?
            AND isCovered >= ?
            ORDER BY slotNo ASC
            LIMIT 1
        """, (needs_ev, needs_cover)).fetchone()

        if slot:
            cursor.execute("""
                UPDATE parking_slots
                SET isOccupied = 1
                WHERE slotNo = ?
            """, (slot["slotNo"],))
            conn.commit()
            message = f"Vehicle parked at Slot {slot['slotNo']}"
            message_type = "success"
        else:
            message = "No slot available"
            message_type = "error"

        conn.close()

    return render_template("park.html", message=message, message_type=message_type)


# ---------------- REMOVE VEHICLE ----------------
@app.route("/remove/<int:slot_no>")
def remove_vehicle(slot_no):
    conn = get_db_connection()
    conn.execute("""
        UPDATE parking_slots
        SET isOccupied = 0
        WHERE slotNo = ?
    """, (slot_no,))
    conn.commit()
    conn.close()

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)