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
    locations_dict[l['employee_id']] = l['employee_id']

### CONSTRUCT DISTANCES OBJECTS ###
total_distance_between_matrix = 0
distances_dict = {}
for distance_obj in distances:
    tuple_distance = (distance_obj["measure_point"], distance_obj["reference_point"])
    distances_dict[tuple_distance] = distance_obj["hours"]
    total_distance_between_matrix += distance_obj["hours"]


### STARTING MODEL THE SOLUTION ###
# INIT MODEL AND ASSIGN NAMING VARIABLES
model = cp_model.CpModel()

# Model JOB_TYPE with optional BOOL_VAR
job_type = collections.namedtuple('booking_type', 'start end interval duration bool_var')
block_type = collections.namedtuple('booking_type', 'start end interval duration')
dummy_type = collections.namedtuple('dummy_type', 'start end interval duration')
all_bookings = {} 

# Model JOBS
for j in jobs:
    for e in employees:
        if j['job_type'] in e['skills'] or 'General' in e['skills']:
            label_tuple = (j['job_id'], e['employee_id'])
            start_var = model.NewIntVar(0, horizon, 'start_assign_%s_%s' % label_tuple)
            duration = j['job_duration']
            end_var = model.NewIntVar(0, horizon, 'end_assign_%s_%s' % label_tuple)
            bool_var = model.NewBoolVar('bool_assign_%s_%s' % label_tuple)
            optional_interval_var = model.NewOptionalIntervalVar(
                start_var, duration, end_var, bool_var,
                'optional_interval_assign_%s_%s' % label_tuple
            )

            all_bookings[label_tuple] = job_type(
                start=start_var, end=end_var, interval=optional_interval_var,
                duration=duration, bool_var=bool_var
            )