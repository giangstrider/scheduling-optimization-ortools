from ortools.sat.python import cp_model
import collections
import datetime
import json
import math

from config import horizon
from helper import get_weekday_from_datetime, get_distance_between_point

with open('sample.json') as f:
    data = json.load(f)

jobs = data['jobs']
blocked_times = data['blocked_times']
employees = data['employees']
locations = data['locations']
distances = data['distances']

### LOGGING SIZE OF DATA TO MEASURE PERFORMANCE ###
print("ASSIGNMENTS ", len(jobs))
print("BLOCKED_TIMES ", len(blocked_times))
print("INSPECTORS ", len(employees))
print("HORIZON ", horizon)


### TRANSFORM DATE OF JOB & BLOCKING_TIMES TO INTEGER ###
for a in jobs:
    a['origin_expected_date'] = a['expected_date']
    a['expected_date'] = get_weekday_from_datetime(a['expected_date'])
    if not a['shipment_date']:
        a['shipment_date'] = -1
    else:
        a['shipment_date'] = get_weekday_from_datetime(a['shipment_date'])

for b in blocked_times:
    b['origin_requested_date'] = b['requested_date']
    b['requested_date'] = get_weekday_from_datetime(b['requested_date'])       

### CONSTRUCT LOCATIONS OBJECTS ###
locations_dict = {}
for l in locations:
    locations_dict[l['factory_customer_id']] = l['employee_id']

### CONSTRUCT DISTANCES OBJECTS ###
total_distance_between_matrix = 0
distances_dict = {}
for distance_obj in distances:
    tuple_distance = (distance_obj["measure_point"], distance_obj["reference_point"])
    distances_dict[tuple_distance] = distance_obj["hours"]
    total_distance_between_matrix += distance_obj["hours"]