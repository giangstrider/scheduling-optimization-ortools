# Employee Scheduling Problems

Using Google Operation Research Tools to solve scheduling problems.

Please refer to this article for more details about the problems (coming soon).

## General

### The problems

The comany have a list of employees and list of jobs need to be done every week.
Each job required specific skills and need to be done in specific locations.
Each employee having their own skills and their home can be near or very far from job's location. Also, each of them having their own calendar, available on different time slots during the week.
Find the solution to satified all of the constraint.

The solution also need to optimize many objects  for example: to help minimize employees travel time, working time and the work also to be done.

### Constraints

- Each job execute by only 1 employee.
- Each job need to done in specific location.
- Employee cannot be working in a time slot which has been blocked on their calendar.
- Jobs executing by employee cannot be overlap.
- Job must be executed before requested date.
- Time slot of employee happen from 6:00AM to 18:00AM, they will not work outside that hours.

### Objectives

- Minimize employee's travelling time: As said above, some employee live very far from job location. Help them to travel least.
- Location change: minimize location change between the jobs, during the week.
- Date Change: Some employee want to finish the work earliest this week. For example, they don't want to work in Friday. Help them finish the work in days before.
- Load balacing: the job need to be balance between employees. Can't be one person finish all the jobs, the others are free.
- Job also have expected date and requested date to finish, it's better finish on expected date, rather than expected date.

## Modeling

This part using lots of term from Google Ortools in specific, and optimization solver in general. Please refer to their documentation for any specific question.

### Decision Var

Model Decision Var by IntVar including:

- JOBS: `[Start, End, BoolVar]` (Starting time, Ending time, Duration, Optional Var: mean this job can be execute by this employee or not)
- BLOCKED_TIMES: `[Start, End]` (This blocked times alway need to be execute by specific employee)
- DUMMY: `[Start, End]` (Model dummy re-present as non-working hour jobs, this dummy to be filled during the week, together with 2 above)

### Specific Var

- LOCATION: model this using CirCuit node. Each location will be a node, also employee's home is considering as a dummy node.

### Multi Objectives

- Each objective has priority weight. Base on that, model the solution follow that priority.

## Build & Run

Install Python 3.7 package with Pipenv and run python file:

```bash
python3 main.py
```

## Sample Results
```
Employee 0230509700
start_79558_U2R8oIWr: Monday-13-7
end_79558: Monday-16-10


Employee 7222247981
start_79558_mefZUjzH: Monday-13-7
end_79558: Monday-16-10
start_block_wonoXGV5: Monday-16-10
end_block_wonoXGV5: Monday-19-13


Employee 8875727446
- None work

Employee 6117206298
start_79558_x7f4bzqP: Monday-13-7
end_79558: Monday-16-10
start_79558_SZntYmCs: Monday-19-13
end_79558: Monday-22-16
start_79558_pPjY3lwB: Monday-16-10
end_79558: Monday-19-13
```

Each employee has their calendar, with a week day, and timeshift attached next to it.

## Modify Sample Data

You can also add more jobs, add more locations and employees.
Just make sure that the sample data will return FEARISLE solution.

Data size increase means solver take longer time to get the solution.

## Perfomance

Using AWS EC2 Instance with sample size

- Coming soon

## Visualization

Coming soon