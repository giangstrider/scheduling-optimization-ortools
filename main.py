from ortools.sat.python import cp_model
import collections
import datetime
import json
import math

from config import horizon, weekdays_int, HOURS_PER_DAY_MODEL
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

# Model BLOCKING_TIMES
for b in blocked_times:
    for e in employees:
        if b['employee_id'] == e['employee_id']:
            label_blocked = b['blocked_id']
            start_var = model.NewIntVar(0, horizon, 'start_block_%s' % label_blocked)
            duration = b['activity_duration']
            end_var = model.NewIntVar(0, horizon, 'end_block_%s' % label_blocked)
            bool_var = model.NewBoolVar('bool_block_%s' % label_blocked)
            interval_var = model.NewIntervalVar(
                start_var, duration, end_var, 'interval_block_%s' % label_blocked
            )

            all_bookings[label_blocked] = block_type(
                start=start_var, end=end_var, interval=interval_var, duration=duration
            )

# Model dummy blocks
for w in weekdays_int:
    for e in employees:
        start_bound = w * HOURS_PER_DAY_MODEL

        # Dummy day
        label_dummy_day = (w, e['employee_id'], 'day')
        end_day_from = start_bound + 6
        start_day_var = model.NewIntVar(
            start_bound, end_day_from, 'start_day_dummy_%i_%s_%s' % label_dummy_day
        )
        end_day_var = model.NewIntVar(
            start_bound, end_day_from, 'end_day_dummy_%i_%s_%s' % label_dummy_day
        )
        duration_day = 6
        day_interval_var = model.NewIntervalVar(
            start_day_var, duration_day, end_day_var, 'interval_day_dummy_%i_%s_%s' % label_dummy_day
        )
        all_bookings[label_dummy_day] = dummy_type(
            start=start_day_var, end=end_day_var, interval=day_interval_var, duration=duration_day
        )

        # Dummy night
        label_dummy_night = (w, e['employee_id'], 'night')
        start_night_from = start_bound + 18
        end_night_from = (w + 1) * HOURS_PER_DAY_MODEL
        start_night_var = model.NewIntVar(
            start_night_from, end_night_from, 'start_night_dummy_%i_%s_%s' % label_dummy_night
        )
        end_night_var = model.NewIntVar(
            start_night_from, end_night_from, 'end_night_dummy_%i_%s_%s' % label_dummy_night
        )
        duration_night = HOURS_PER_DAY_MODEL - 18
        night_interval_var = model.NewIntervalVar(
            start_night_var, duration_night, end_night_var, 'interval_night_dummy_%i_%s_%s' % label_dummy_night
        )
        all_bookings[label_dummy_night] = dummy_type(
            start=start_night_var, end=end_night_var, interval=night_interval_var, duration=duration_night
        )


### CONSTRAINT AND OBJECTIVE FORMULATION ###
# Each job execute by only 1 employee & load balancing | location mapping objective formulation
diff_of_vector_balancing = []
avg_jobs_of_employees = int(len(jobs) / len(employees))
max_diff_balancing_integer = len(jobs) - avg_jobs_of_employees
max_diff_balancing_var = model.NewIntVar(0, max_diff_balancing_integer, 'max_diff_balancing')
bools_factory_mapping = []
for j in jobs:
    bool_jobs = []
    for e in employees:
        if j['job_type'] in e['skills'] or 'General' in e['skills']:
            label_tuple = (j['job_id'], e['employee_id'])
            bool_jobs.append(all_bookings[label_tuple].bool_var)
            if locations_dict[j['location_id']] == e['employee_id']:
                bools_factory_mapping.append(all_bookings[label_tuple].bool_var.Not())
    model.Add(sum(bool_jobs) == 1)

    # Model load balancing objective
    diff_var = model.NewIntVar(-avg_jobs_of_employees, max_diff_balancing_integer, 'diff_with_avg_%s' % a['job_id'])
    model.Add(diff_var == sum(bool_jobs) - avg_jobs_of_employees)
    abs_diff_of_balancing_var = model.NewIntVar(0, max_diff_balancing_integer, 'abs_diff_with_avg_%s' % a['job_id'])
    model.AddAbsEquality(abs_diff_of_balancing_var, diff_var)
    diff_of_vector_balancing.append(abs_diff_of_balancing_var)