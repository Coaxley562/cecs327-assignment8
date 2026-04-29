ASSIGNMENT 8 CECS 327
BAILEY COKLEY

--THE SETUP--

Okay so we got ONE dependency (psycopg2, it lets python connect to a postgres database and query it.)
SO...run the following:

pip install psycopg2-binary


--HOW TO RUN THE FILES--

Okay so on the Server machine run the following:
python server.py


THEN on the client machine run the following:
python client.py

Then enter the servers public IP and port 12345 when it prompts you to (nothing new to us)

As the assignment details said, it supports these following queries:

1) What is the average moisture inside our kitchen fridges in the past hours, week and month? 
2) What is the average water consumption per cycle across our smart dishwashers in the past hour, week and month? 
3) Which house consumed more electricity in the past 24 hours, and by how much? 

of course, any other input will give an error message 

--THE SYSTEM'S ARCHITECTURE--

DataNiz (Virtual IoT Devices)
        |
    MQTT Broker
        |
    NeonDB (table_virtual)
        |
   TCP Server <-----> TCP Client


--MY TWO HOUSE DESIGN--

Since I did this by myself, i simulated the two-house setup using two separate DataNiz refrigerator devices:

- House A: Smart Refrigerator (`parent_asset_uid: 4wi-ljx-fg6-ew8`)
- House B: Smart Refrigerator Duplicate (`parent_asset_uid: 1177970d-c71e-46b7-9b2f-6219c23ea42d`)
- Dishwasher: belongs to House A (`parent_asset_uid: 44e-957-12f-741`)

Hardcoding the value of the timestamp `SHARING_START` to (`2026-04-11 12:00 UTC`) simulates the start of sharing of data by House B. The server can then report how many records from House B fall before or after this timestamp.

--DEVICE METADATA--

The below format is like this: | Device | Asset UID | Sensors |

| Smart Refrigerator (House A) | 4wi-ljx-fg6-ew8 | Moisture (%), Ammeter (A), Thermistor (°C) |
| Smart Refrigerator Duplicate (House B) | 1177970d-c71e-46b7-9b2f-6219c23ea42d | Moisture (%), Ammeter (A), Thermistor (°C) |
| Smart Dishwasher (House A) | 44e-957-12f-741 | Water Level (mL), Temperature (°C) |

The metadata fields i used are: `parent_asset_uid`, `board_name`, `asset_uid` 
    i used these to 1- route records to its cooresponding house and 2- identify which sensor is producing the reading

--Calculations, Assumptions--

Moisture: the raw sensor value of the moisture sensor of 0-100 is reported as a percentage directly
Water consumption: the raw sensor value of the water consumption sensor of 0-2000 is in mL per cycle, but must be converted to gallons by multiplying by 0.000264172
Electricity: the current of the unit in amps (A) is multiplied by the voltage (120V) in the unit, then the amount of time the unit was cycling in minutes is divided by 60 to get the number of hours that the unit was cycling (5 min / 60). The product of these three factors is in Wh, but must be divided by 1000 to get kWh --> actual formula: `(|current (A)| × 120V × (5 min / 60))/1000`

All values will be reported in PST (UTC-7)
The queries are defined as a linked list of (query_string, handler) pairs


--DISTRIBUTED QUERY COMPLETENESS--
The server FIRST checks if there are any records in House B before and after the sharing started. Then it returns the count of the records to the server in the response. 
If the time window predates the sharing agreement, the server will report the count of the records in House B prior to the sharing beginning.



Part A Information:

1) The server uses psycopg2 to connect to NeonDB using the connection string. It then queries the database for the table_virtual database and filters for the records with the parent_asset_uid to get the data from the device of interest.
2) Distributed query processing is implemented by fetching the data for each house separately and then combining that data on the server so that the client receives a single answer to the query.
3) The query processing logic determines whether the records from House B should be examined for whether they fall before or after the sharing start timestamp. If they fall before that timestamp, the server will note the number of such records so that the system is aware that the query may return incomplete data in a distributed system.
4) The system uses the metadata fields of the records (specifically the parent_asset_uid, board_name, and asset_uid fields) to determine which house owns each record, and to route the records to the correct query handler that will process the record. The sharing feature between the two houses is simulated by a hardcoded timestamp that indicates when House B started sharing its data with House A.