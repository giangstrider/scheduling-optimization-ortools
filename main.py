from ortools.sat.python import cp_model
import collections
import datetime
import json
import math

from config import horizon, weekdays_int, HOURS_PER_DAY_MODEL, CONFIGS, search_workers, log_search_progress, max_time_in_seconds
from helper import get_weekday_from_datetime, get_distance_between_point, get_bound_of_weekday, integer_to_day_hour

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
print("EMPLOYEES ", len(employees))
print("HORIZON ", horizon)


### TRANSFORM DATE OF JOB & BLOCKING_TIMES TO INTEGER ###
for j in jobs:
    j['origin_expected_date'] = j['expected_date']
    j['expected_date'] = get_weekday_from_datetime(j['expected_date'])
    if not j['shipment_date']:
        j['shipment_date'] = -1
    else:
        j['shipment_date'] = get_weekday_from_datetime(j['shipment_date'])

for b in blocked_times:
    b['origin_requested_date'] = b['requested_date']
    b['requested_date'] = get_weekday_from_datetime(b['requested_date'])       

### CONSTRUCT LOCATIONS OBJECTS ###
locations_dict = {}
for l in locations:
    locations_dict[l['location_id']] = l['employee_id']

print(locations_dict)   

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
            duration = b['job_duration']
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
bools_location_mapping = []
for j in jobs:
    bool_jobs = []
    for e in employees:
        if j['job_type'] in e['skills'] or 'General' in e['skills']:
            label_tuple = (j['job_id'], e['employee_id'])
            bool_jobs.append(all_bookings[label_tuple].bool_var)
            if locations_dict[j['location_id']] == e['employee_id']:
                bools_location_mapping.append(all_bookings[label_tuple].bool_var.Not())
    model.Add(sum(bool_jobs) == 1)

    # Model load balancing objective
    diff_var = model.NewIntVar(-avg_jobs_of_employees, max_diff_balancing_integer, 'diff_with_avg_%s' % j['job_id'])
    model.Add(diff_var == sum(bool_jobs) - avg_jobs_of_employees)
    abs_diff_of_balancing_var = model.NewIntVar(0, max_diff_balancing_integer, 'abs_diff_with_avg_%s' % j['job_id'])
    model.AddAbsEquality(abs_diff_of_balancing_var, diff_var)
    diff_of_vector_balancing.append(abs_diff_of_balancing_var)

model.AddMaxEquality(max_diff_balancing_var, diff_of_vector_balancing)


# Model date change
abs_integer_dates_distance = []
# Travel time objective
switch_transit_literals = []
switch_transition_times = []
# Distance objective
total_avg_distances = 0
for e in employees:
    intervals = []
    executor_starts = []
    executor_ends = []
    executor_bools = []
    executor_intervals = []
    location_ids_mapping = []

    distance_i_to_fs = 0
    # NoOverLap contraint for assignments
    for j in jobs:
        if j['job_type'] in e['skills'] or 'General' in e['skills']:
            label_tuple = (j['job_id'], e['employee_id'])
            booking = all_bookings[label_tuple]

            # Add to list for NoOverlap constraint
            intervals.append(booking.interval)
            # Add to executor node for dense graph
            executor_intervals.append(booking.interval)

            # Add to executor node for dense graph distance reference
            executor_starts.append(booking.start)
            executor_ends.append(booking.end)

            # Add to executor bool for dense graph node reference
            executor_bools.append(booking.bool_var)

            # Add to executor bool for dense graph location mapping
            location_ids_mapping.append(j['location_id'])

            # Booking must happens before shipment date (deadline)
            if j['shipment_date'] >= 0:
                deadline_start_bound, deadline_end_bound = get_bound_of_weekday(
                    HOURS_PER_DAY_MODEL, j['shipment_date'], 6, 18
                )
                model.Add(booking.end <= deadline_end_bound)

            # Model variable for date change objective
            integer_date_of_assignment_var = model.NewIntVar(
                0, weekdays_int[-1], 'integer_date_assignment_%s_%s' % label_tuple
            )
            integer_dates_distance_var = model.NewIntVar(
                -weekdays_int[-1], weekdays_int[-1], 'integer_date_distance_%s_%s' % label_tuple
            )
            abs_distance_var = model.NewIntVar(
                0, weekdays_int[-1], 'integer_date_distance_abs_%s_%s' % label_tuple
            )
            model.AddDivisionEquality(integer_date_of_assignment_var, booking.start, HOURS_PER_DAY_MODEL)
            model.Add(integer_date_of_assignment_var - j['expected_date'] == integer_dates_distance_var)
            model.AddAbsEquality(abs_distance_var, integer_dates_distance_var)
            abs_integer_dates_distance.append(abs_distance_var)

            # Traveling time object avg
            distance = get_distance_between_point(
                distances_dict, e['employee_id'], j['location_id']
            )
            distance_i_to_fs += distance

    avg_distance_from_i_to_fs = int(distance_i_to_fs / len(employees))
    total_avg_distances += avg_distance_from_i_to_fs

    for b in blocked_times:
        if b['employee_id'] == e['employee_id']:
            label_blocked = b['blocked_id']
            booking = all_bookings[label_blocked]

            # Add to list for NoOverlap constraint
            intervals.append(booking.interval)

            # Booking must happens in requested_date date
            block_start_bound, block_end_bound = get_bound_of_weekday(
                HOURS_PER_DAY_MODEL, b['requested_date'], 6, 18
            )
            model.Add(all_bookings[label_blocked].start >= block_start_bound)
            model.Add(all_bookings[label_blocked].end <= block_end_bound)

    dummy_bools = []
    for w in weekdays_int:
        label_dummy_day = (w, e['employee_id'], 'day')
        booking_day = all_bookings[label_dummy_day]

        label_dummy_night = (w, e['employee_id'], 'night')
        booking_night = all_bookings[label_dummy_night]

        # Add to list for NoOverlap constraint
        intervals.append(booking_day.interval)
        intervals.append(booking_night.interval)
        # Add to executor node for dense graph
        executor_intervals.append(booking_day.interval)
        executor_intervals.append(booking_night.interval)

        bool_day = model.NewBoolVar('day_dummy_%i_%s_%s' % label_dummy_day)
        bool_night = model.NewBoolVar('night_dummy_%i_%s_%s' % label_dummy_night)
        # Add to bools list to indicate successor of dense graph
        dummy_bools.append(bool_day)
        dummy_bools.append(bool_night)
        # Add to executor bool for dense graph node reference
        executor_bools.append(bool_day)
        executor_bools.append(bool_night)
        # Add to executor bool for dense graph comparing distance
        executor_starts.append(booking_day.start)
        executor_starts.append(booking_night.start)
        executor_ends.append(booking_day.end)
        executor_ends.append(booking_night.end)

        location_ids_mapping.append(e['employee_id'])
        location_ids_mapping.append(e['employee_id'])

    # Enable to True all of dummy block
    model.Add(sum(dummy_bools) == len(weekdays_int * 2))

    # Non overlap all tasks
    model.AddNoOverlap(intervals)

    # Model Distance and Objectives: travel time - location change
    arcs = []
    for idx_i, a_i in enumerate(executor_intervals):
        # dummy node of CIRCUIT
        start_literal = model.NewBoolVar('%i_first_job' % idx_i)
        end_literal = model.NewBoolVar('%i_last_job' % idx_i)
        arcs.append([0, idx_i + 1, start_literal])
        arcs.append([idx_i + 1, 0, end_literal])
        # Self arc if the assignment is not performed.
        arcs.append([idx_i + 1, idx_i + 1, executor_bools[idx_i].Not()])
        i_point = location_ids_mapping[idx_i]

        for idx_j, a_j in enumerate(executor_intervals):
            if idx_i == idx_j:
                continue

            literal = model.NewBoolVar('%i_follows_%i' % (idx_j, idx_i))
            arcs.append([idx_i + 1, idx_j + 1, literal])
            model.AddImplication(literal, executor_bools[idx_i])
            model.AddImplication(literal, executor_bools[idx_j])

            j_point = location_ids_mapping[idx_j]
            # Constraint distance if j is successor of i
            if i_point != j_point:
                # Constraint distance location <-> location
                i_to_j_distance = get_distance_between_point(
                    distances_dict, i_point, j_point
                )

                # Add to objective for location change and transition times
                switch_transit_literals.append(literal)
                switch_transition_times.append(i_to_j_distance)
            else:
                i_to_j_distance = 0

            # Reified transition to link the literals with the times
            model.Add(
                executor_starts[idx_j] >= executor_ends[idx_i] + i_to_j_distance
            ).OnlyEnforceIf(literal)

    model.AddCircuit(arcs)


### OBJECTIVES ###
# Modeling normalize traveling time
result_traveling_time_var = model.NewIntVar(0, total_distance_between_matrix, 'result_traveling_time')
traveling_time_objective_var = model.NewIntVar(0, total_distance_between_matrix, 'traveling_time_objective')
model.Add(sum([
    s * switch_transition_times[idx] for idx, s in enumerate(switch_transit_literals)
]) == result_traveling_time_var)
model.AddDivisionEquality(
    traveling_time_objective_var, result_traveling_time_var, total_avg_distances
)

# MODEL MUTIPLE OBJECTS BY PRIORITY WEIGHT
weights = [5 - val for key, val in CONFIGS.items()]
objectives = [
    sum(bools_location_mapping), 
    traveling_time_objective_var,
    sum(abs_integer_dates_distance),
    max_diff_balancing_var
]

model.Minimize(sum([w * objectives[idx] for idx, w in enumerate(weights)]))

# Solve problem with model
solver = cp_model.CpSolver()
solver.parameters.num_search_workers = search_workers
solver.parameters.log_search_progress = log_search_progress
solver.parameters.max_time_in_seconds = 24 * 60 * 60
status = solver.Solve(model)

print('  - status          : %s' % solver.StatusName(status))
print('  - conflicts       : %i' % solver.NumConflicts())
print('  - branches        : %i' % solver.NumBranches())
print('  - wall time       : %f s' % solver.WallTime())
print('  - Objective       : %f s' % solver.ObjectiveValue())

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    for e in employees:
        print("Employee %s" % e['employee_id'])
        for j in jobs:
            if j['job_type'] in e['skills'] or 'General' in e['skills']:
                label_tuple = (j['job_id'], e['employee_id'])
                if solver.BooleanValue(all_bookings[label_tuple].bool_var):
                    
                    name_start = 'start_%s_%s' % (j['location_id'], j['job_id'])
                    name_end = 'end_%s' %(j['location_id'])


                    value_start = integer_to_day_hour(solver.Value(all_bookings[label_tuple].start), True)  + "-" + str(solver.Value(all_bookings[label_tuple].start))
                    value_end = integer_to_day_hour(solver.Value(all_bookings[label_tuple].end), False)  + "-" + str(solver.Value(all_bookings[label_tuple].end))
                    print(name_start + ": " + value_start)
                    print(name_end + ": " + value_end)

        for b in blocked_times:
            if b['employee_id'] == e['employee_id']:
                label_blocked = b['blocked_id']
                name_start = 'start_block_%s' % label_blocked
                name_end = 'end_block_%s' % label_blocked
                value_start = integer_to_day_hour(solver.Value(all_bookings[label_blocked].start), True) + "-" + str(solver.Value(all_bookings[label_blocked].start))
                value_end = integer_to_day_hour(solver.Value(all_bookings[label_blocked].end), False) + "-" + str(solver.Value(all_bookings[label_blocked].end))
                print(name_start + ": " + value_start)
                print(name_end + ": " + value_end)

        print("")
        print("")