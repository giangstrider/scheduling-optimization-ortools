################### OPTIMIZATION FATOR ###################
# PRIORITY FACTOR RANKED BY INTEGER FROM HIGHEST (SMALLEST INTEGER) TO LOWEST
CONFIGS = {
    "location_change": 1,
    "travel_time": 2,
    "date_change": 3,
    "load_balancing": 4
}

# NUMBER OF WORKING DAYS PER WEEK CONVERT TO INTEGER
days_per_week = 5
weekdays_int = list(range(0, days_per_week))

# NUMBER OF HOUR PER DAY INCLUDING NON-WORKING HOUR
HOURS_PER_DAY_MODEL = 24

# NUMBER OF HOUR PER WEEK INCLUDING NON-WORKING HOUR
horizon = days_per_week * HOURS_PER_DAY_MODEL


###################### SOLVER CONFIGURATION ###################
# NUMBER OF PARALLEL WORKERS FOR RUNNING SOLVER. USUALLY THIS EQUAL TO NUMBER OF CPU
search_workers = 12

# OPTION PRINT LOG SEARCH DURING SOLVING PROBLEMS
log_search_progress = True

# LIMIT TIME TO SOLVE TO THE PROBLEMS IN SECONDS
max_time_in_seconds = 24 * 60 * 60
