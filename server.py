import socket
import psycopg2
import json
from datetime import datetime, timedelta, timezone

# connection string
DB_URL = "postgresql://neondb_owner:npg_0ioNCmzB7kQV@ep-falling-truth-anrj39wl-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
PORT = 12345

# house A is the og fridge... house B is the duplicate one i made for assignment 7
# dishwasher belongs to house A bc i only have one
HOUSE_A_FRIDGE = "4wi-ljx-fg6-ew8"
HOUSE_B_FRIDGE = "1177970d-c71e-46b7-9b2f-6219c23ea42d"
DISHWASHER = "44e-957-12f-741"

# these are the exact key names dataniz put in the json payload (had to dig for these bad boys)
MOISTURE_KEY = "Capacitive Soil Moisture Sensor - Moisture"
AMMETER_KEY = "ACS712 - Ammeter"
WATER_KEY = "Capacitive Liquid Level Sensor - Water Level Sensor"

# this is when i "enabled sharing" between the two houses
# data before this = pre-sharing & data after = post-sharing
SHARING_START = datetime(2026, 4, 11, 12, 0, 0, tzinfo=timezone.utc)

PST = timezone(timedelta(hours=-7))  # technically PDT but close enough

def get_conn():
    return psycopg2.connect(DB_URL)

def to_pst(dt):
    if dt is None:
        return None
    return dt.astimezone(PST)

# grabs rows from the db for a specific device + sensor within a time window
def fetch_rows(conn, device_uid, sensor_key, since):
    cur = conn.cursor()
    cur.execute("""
        SELECT payload->%s, time
        FROM table_virtual
        WHERE payload->>'parent_asset_uid' = %s
          AND payload->%s IS NOT NULL
          AND time >= %s
    """, (sensor_key, device_uid, sensor_key, since))
    rows = cur.fetchall()
    cur.close()
    return rows

#Averages the sensor values from a list of rows, skips da bad ones
def avg_vals(rows):
    vals = []
    for r in rows:
        try:
            vals.append(float(json.loads(r[0]) if r[0].startswith('"') else r[0]))
        except:
            pass
    return sum(vals) / len(vals) if vals else 0.0

# query NUMBER ONEE: the average moisture across both fridges in the two houses!
def q1_moisture(conn):
    now = datetime.now(timezone.utc)
    windows = {
        "past hour": now - timedelta(hours=1),
        "past week": now - timedelta(weeks=1),
        "past month": now - timedelta(days=30),}
    lines = ["=== Average Fridge Moisture (%) ==="]
    for label, since in windows.items():
        rows_a = fetch_rows(conn, HOUSE_A_FRIDGE, MOISTURE_KEY, since)
        rows_b = fetch_rows(conn, HOUSE_B_FRIDGE, MOISTURE_KEY, since)
        avg = avg_vals(rows_a + rows_b)
        pre = [r for r in rows_b if r[1] < SHARING_START]
        post = [r for r in rows_b if r[1] >= SHARING_START]
        note = f"(House B: {len(pre)} pre-sharing + {len(post)} post-sharing records)"
        lines.append(f"  {label}: {avg:.2f}% {note}")
    return "\n".join(lines)

# query NUMBER TWOO: the average water usage per dishwasher cycle
# The sensor outputs 0-2000, It's mL, so just have to convert it to gallons.
def q2_water(conn):
    now = datetime.now(timezone.utc)
    windows = {
        "past hour": now - timedelta(hours=1),
        "past week": now - timedelta(weeks=1),
        "past month": now - timedelta(days=30),}
    lines = ["=== Average Dishwasher Water Consumption per Cycle ==="]
    for label, since in windows.items():
        rows = fetch_rows(conn, DISHWASHER, WATER_KEY, since)
        avg_raw = avg_vals(rows)
        avg_gal = avg_raw * 0.000264172
        lines.append(f"  {label}: {avg_raw:.2f} mL ({avg_gal:.4f} gallons) — {len(rows)} records")
    return "\n".join(lines)

#query NUMBER THREEE: which of the two houses, in the past 24 hours, used more electricity?? 
#the complex ahh formula is -> |amps| * 120V * (5min/60) per reading = watt-hours, so sum and convert to kWh
def q3_electricity(conn):
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    rows_a = fetch_rows(conn, HOUSE_A_FRIDGE, AMMETER_KEY, since)
    rows_b = fetch_rows(conn, HOUSE_B_FRIDGE, AMMETER_KEY, since)
    VOLTAGE = 120
    INTERVAL_HR = 5 / 60
    def kwh(rows):
        total = 0.0
        for r in rows:
            try:
                amps = abs(float(json.loads(r[0]) if r[0].startswith('"') else r[0]))
                total += amps * VOLTAGE * INTERVAL_HR
            except:
                pass
        return total / 1000
    kwh_a = kwh(rows_a)
    kwh_b = kwh(rows_b)
    pre_b = [r for r in rows_b if r[1] < SHARING_START]
    post_b = [r for r in rows_b if r[1] >= SHARING_START]
    winner = "House A" if kwh_a > kwh_b else "House B"
    diff = abs(kwh_a - kwh_b)
    lines = [
        "== Electricity Consumption (Past 24 Hours) ==",
        f"  House A (Smart Refrigerator):           {kwh_a:.4f} kWh",
        f"  House B (Smart Refrigerator Duplicate): {kwh_b:.4f} kWh",
        f"  House B: {len(pre_b)} pre-sharing + {len(post_b)} post-sharing records",
        f"  --> {winner} consumed more electricity by {diff:.4f} kWh",
        f"  (formula: |current| x 120V x 5min interval, converted to kWh)",
        f"  (PST timestamp: {to_pst(now).strftime('%Y-%m-%d %H:%M %Z')})",]
    return "\n".join(lines)

# linked list style dispatch...iterates through until it finds a match
QUERY_MAP = [
    ("What is the average moisture inside our kitchen fridges in the past hours, week and month?", q1_moisture),
    ("What is the average water consumption per cycle across our smart dishwashers in the past hour, week and month?", q2_water),
    ("Which house consumed more electricity in the past 24 hours, and by how much?", q3_electricity),]

def handle(msg, conn):
    for query_str, fn in QUERY_MAP:
        if msg.strip() == query_str:
            return fn(conn)
    return "Sorry twin...can't process this query. Please try one of the supported queries."

# startup
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('', PORT))
server.listen(1)
print("Server listening on port", PORT)
conn_db = get_conn()
print("Connected to NeonDB")
conn, addr = server.accept()
print("Connected by", addr)
while True:
    data = conn.recv(4096)
    if not data:
        break
    msg = data.decode()
    print("Received:", msg)
    response = handle(msg, conn_db)
    conn.send(response.encode())
conn.close()
conn_db.close()