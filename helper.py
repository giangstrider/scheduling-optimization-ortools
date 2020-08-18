import math
import datetime

def integer_to_day_hour(num_integer, within_day=True, num_hours_per_day=24, start_hour_of_day=6):
    """Convert integer return from solver to readable date for logging or visualization."""
    plus_number = num_integer % num_hours_per_day
    hours = start_hour_of_day + plus_number
    day = math.floor(num_integer / num_hours_per_day)
    if plus_number == 0 and day != 0 and not within_day:
        day = day - 1
        hours = start_hour_of_day + num_hours_per_day

    date = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][day]
    string_return = date + "-" + str(hours)
    return string_return

def get_weekday_from_datetime(dt):
    year, month, day = (int(x) for x in dt.split('-'))
    weekday = datetime.date(year, month, day).weekday()
    return weekday

def get_distance_between_point(distances_dict, measure_point, reference_point):
    """Returns the distance between tasks of job measure_point and tasks of job reference_point."""
    key_tuple = (measure_point, reference_point)
    if key_tuple not in distances_dict.keys():
        key_tuple = (reference_point, measure_point)
    hours = distances_dict[key_tuple]
    return hours

def get_bound_of_weekday(hours_per_day_model, weekday, hour_from, hour_to):
    start_bound = weekday * hours_per_day_model + hour_from
    end_bound = start_bound + hour_to - hour_from
    return start_bound, end_bound
