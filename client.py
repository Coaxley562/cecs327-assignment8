#This is the client file with all that logic the client program has to use :D
import socket

QUERIES = {
    "1": "What is the average moisture inside our kitchen fridges in the past hours, week and month?",
    "2": "What is the average water consumption per cycle across our smart dishwashers in the past hour, week and month?",
    "3": "Which house consumed more electricity in the past 24 hours, and by how much?", }
server_ip = input("Enter server IP: ")
port = int(input("Enter port number: "))
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect((server_ip, port))
except:
    print("Error connecting to server")
    exit()
print("\nSupported queries:")
for k, v in QUERIES.items():
    print(f"  [{k}] {v}")
print("  [quit] Exit\n")

while True:
    choice = input("Greetings twin. Please enter query number (1/2/3) or 'quit': ").strip()
    if choice == "quit":
        break
    if choice not in QUERIES:
        print("Sorry twin, this query cant be processed. Try one of the supported queries.\n")
        continue
    msg = QUERIES[choice]
    client.send(msg.encode())
    response = client.recv(4096)
    print("\nServer response:")
    print(response.decode())
    print()
client.close()