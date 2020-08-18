from ortools.sat.python import cp_model
import collections
import datetime
import json
import math

with open('sample.json') as f:
    data = json.load(f)

jobs = data['jobs']
blocked_times = data['blocked_times']
employees = data['employees']
factories = data['location']
distances = data['distances']

### LOGGING SIZE OF DATA TO MEASURE PERFORMANCE ###
print("ASSIGNMENTS ", len(jobs))
print("BLOCKED_TIMES ", len(blocked_times))
print("INSPECTORS ", len(employees))
print("HORIZON ", horizon)