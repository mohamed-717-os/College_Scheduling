import pulp
import os
import math

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# /////////////////////  Data //////////////////////

HALLS = 4  # number of halls
LABS  = 9   # number of labs
DAYS    = list(range(1,6))  # 1..5
PERIODS = list(range(1,6))  # 1..5

        # ------------------------------------------- #

environments = ['year1', 'year2']

groups = {
    'year1': ['G1','G2'],
    'year2': ['G3', 'G4'],
}

classes = {
    'G1': ['C1','C2', 'C3'],
    'G2': ['C1','C2', 'C3'],
    'G3': ['C1','C2'],
    'G4': ['C1','C2', 'C3'],
}

subjects = {
    'year1': ['Math','CS', 'Algo1', 'AI', 'Graphics'],
    'year2': ['Algo2','DataSci','ML', 'DL',],
}

subj_list = {s for e in environments for s in subjects[e]}
subj_list = list(subj_list)
        # ------------------------------------------- #

A = ['eng.Mohamed','eng.Ali','eng.Youssef', 'eng.Alaa', 'eng.Hassan']   # Teacher Assistants
T = ['Dr.Omar','Dr.Youssef','Dr.Waleed']     # Doctors

AL = [8, 3]   # maximum load for assistant (periods per week, subjects)
TA = [5, 3]  # maximum load for Doctor (periods per week, subjects)


# AT[a][d][p] = 1 if TA a prefers time (d,p), else 0
AT = {a: {d: {p: 1 for p in PERIODS} for d in DAYS} for a in A}
TT = {t: {d: {p: 1 for p in PERIODS} for d in DAYS} for t in T}

# AS[a][s] = 1 if TA a want to teach subject s, else 0
AS = {a: {s: 0 for s in subj_list} for a in A}
TS = {t: {s: 0 for s in subj_list} for t in T}

        # ---------------------------------------------------------- #
        #   select random  preferences for Assestans and Doctors     #

import random

AT = {}
for a in A:
    AT[a] = {d: {p: 1 for p in PERIODS} for d in DAYS}
    blocked = random.sample([(d, p) for d in DAYS for p in PERIODS], 5)
    for d, p in blocked:
        AT[a][d][p] = 0

TT = {}
for t in T:
    TT[t] = {d: {p: 1 for p in PERIODS} for d in DAYS}
    blocked = random.sample([(d, p) for d in DAYS for p in PERIODS], 5)
    for d, p in blocked:
        TT[t][d][p] = 0

AS = {}
for a in A:
    preferred = random.sample(subj_list, 3)
    AS[a] = {s: (1 if s in preferred else 0) for s in subj_list}

TS = {}
for t in T:
    preferred = random.sample(subj_list, 3)
    TS[t] = {s: (1 if s in preferred else 0) for s in subj_list}

        
# ///////////////////// Model /////////////////////
model = pulp.LpProblem("College_Scheduling", pulp.LpMinimize)

# --- Decision Variables ---
Y = pulp.LpVariable.dicts(
    "Lecture",
    [(e,g,c,s,d,p) 
      for e in environments 
      for g in groups[e]
      for c in classes[g]
      for s in subjects[e]
      for d in DAYS 
      for p in PERIODS],
    cat='Binary'
)

X = pulp.LpVariable.dicts(
    "Section",
    [(e,g,c,s,d,p)
      for e in environments
      for g in groups[e]
      for c in classes[g]
      for s in subjects[e]
      for d in DAYS
      for p in PERIODS],
    cat='Binary'
)

BP = pulp.LpVariable.dicts(
    "BusyPeriod",
    [(e,g,c,d,p)
      for e in environments
      for g in groups[e]
      for c in classes[g]
      for d in DAYS
      for p in PERIODS],
    cat='Binary'
)

BD = pulp.LpVariable.dicts(
    "BusyDay",
    [(e,g,c,d)
      for e in environments
      for g in groups[e]
      for c in classes[g]
      for d in DAYS],
    cat='Binary'
)

        # ------------------------------------------- #

I = pulp.LpVariable.dicts(
    "DoctorsIndexer",
    [(t,e,g,c,s,d,p)
      for t in T
      for e in environments
      for g in groups[e]
      for c in classes[g]
      for s in subj_list
      for d in DAYS
      for p in PERIODS],
    cat='Binary'
)

J = pulp.LpVariable.dicts(
    "assistantIndexer",
    [(a,e,g,c,s,d,p)
      for a in A
      for e in environments
      for g in groups[e]
      for c in classes[g]
      for s in subj_list
      for d in DAYS
      for p in PERIODS],
    cat='Binary'
)
# the days that will be assigned to teachers
ADS = pulp.LpVariable.dicts(
    "AssistantDay",
    [(a,s)
      for a in A
      for s in subj_list],
    cat='Binary'
)

TDS = pulp.LpVariable.dicts(
    "DoctorDay",
    [(t,s)
      for t in T
      for s in subj_list],
    cat='Binary'
)

        # ------------------------------------------- #

Load = pulp.LpVariable.dicts(
    "studentDayLoad",
    [(e,g,c,d)
      for e in environments
      for g in groups[e]
      for c in classes[g]
      for d in DAYS],
    cat='Integer'
)

DEV = pulp.LpVariable.dicts(
    "studentDayDeviation",
    [(e,g,c,d)
      for e in environments
      for g in groups[e]
      for c in classes[g]
      for d in DAYS],
    cat='Integer'
)

FP = pulp.LpVariable.dicts(
    "FirstPeriod",
    [(e,g,c,d)
      for e in environments
      for g in groups[e]
      for c in classes[g]
      for d in DAYS],
    cat='Integer'
)

LP = pulp.LpVariable.dicts(
    "LastPeriod",
    [(e,g,c,d)
      for e in environments
      for g in groups[e]
      for c in classes[g]
      for d in DAYS],
    cat='Integer'
)

# ---------------------------------------

# Hall capacity
for d in DAYS:
    for p in PERIODS:
        model += (
            pulp.lpSum(Y[e,g,classes[g][0],s,d,p] 
                       for e in environments 
                       for g in groups[e] 
                       for s in subjects[e])
            <= HALLS,
            f"HallCap_{d}_{p}"
        )

# Lab capacity
        model += (
            pulp.lpSum(X[e,g,c,s,d,p] 
                       for e in environments 
                       for g in groups[e] 
                       for c in classes[g]
                       for s in subjects[e])
            <= LABS,
            f"LabCap_{d}_{p}"
        )

# ---------------------------------------

# Each lecture exactly once
for e in environments:
    for g in groups[e]:
        for c in classes[g]:
            for s in subjects[e]:
                model += (
                    pulp.lpSum(Y[e,g,c,s,d,p] for d in DAYS for p in PERIODS) == 1,
                    f"LectureOnce_{e}_{g}_{c}_{s}"
                )

# Each section per group once
                model += (
                    pulp.lpSum(X[e,g,c,s,d,p] for d in DAYS for p in PERIODS) == 1,
                    f"SectionOnce_{e}_{g}_{c}_{s}"
                )


# Link study‐day indicator
            for d in DAYS:
                for p in PERIODS:
                    
                    Busyperiod = ( 
                        pulp.lpSum(X[e,g,c,s,d,p] for s in subjects[e]) +
                        pulp.lpSum(Y[e,g,c,s,d,p] for s in subjects[e])
                    )

                    model += (Busyperiod <= 1 , f"NoDouble_{e}_{g}_{c}_{d}_{p}")
                    model += (BP[e,g,c,d,p] == Busyperiod , f"Link_BP_{e}_{g}_{c}_{d}_{p}")


                sessions = (
                    pulp.lpSum(X[e,g,c,s,d,p] for s in subjects[e] for p in PERIODS) +
                    pulp.lpSum(Y[e,g,c,s,d,p] for s in subjects[e] for p in PERIODS)
                )
                # If any session ⇒ z=1
                model += (sessions >= BD[e,g,c,d], f"Zone_{e}_{g}_{c}_{d}")
                # If no sessions ⇒ z=0
                model += (sessions <= len(PERIODS) * BD[e,g,c,d], f"Zzero_{e}_{g}_{c}_{d}")


# All classes of the same group takes the lecture together
        for s in subjects[e]:
          for d in DAYS:
              for p in PERIODS:
                model += (           # if the first class takes the lecture, all classes of the same group takes the lecture together
                    pulp.lpSum(Y[e,g,c,s,d,p] for c in classes[g]) == (len(classes[g]) * Y[e,g, classes[g][0] ,s,d,p]),
                    f"GroupClass_{e}_{g}_{s}_{d}_{p}"
                )

# ---------------------------------------

# Assistant period Load per week
for a in A:
    model += (
        pulp.lpSum(J[a,e,g,c,s,d,p] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e] for d in DAYS for p in PERIODS) <= AL[0],
        f"AssistantLoad_{a}"
    )

# Doctor period Load per week
for t in T:
    model += (
        pulp.lpSum(I[t,e,g,c,s,d,p] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e] for d in DAYS for p in PERIODS) <= TA[0],
        f"DoctorLoad_{t}"
    )

# Assistant subject Load 
for a in A:
    model += (
        pulp.lpSum(ADS[a,s] for s in subj_list) <= AL[1],
        f"AssistantLoadSubject_{a}"
    )

# Doctor subject Load 
for t in T:
    model += (
        pulp.lpSum(TDS[t,s] for s in subj_list) <= TA[1],
        f"DoctorLoadSubject_{t}"
    )

# ---------------------------------------
for e in environments:
    for g in groups[e]:
        for c in classes[g]:
            for d in DAYS:
                
                # day study periods for each section
                model += (
                    pulp.lpSum(BP[e,g,c,d,p] for p in PERIODS) == Load[e,g,c,d],
                    f"dayLoad_{e}_{g}_{c}_{d}"
                )

                # achive mean load:     DEV >= | Load - len(PERIODS)/2 |
                model += (
                    DEV[e,g,c,d] >= Load[e,g,c,d] - math.ceil(len(PERIODS)/2),
                    f"dayDeviationPositive_{e}_{g}_{c}_{d}"
                )

                model += (
                    DEV[e,g,c,d] >= math.ceil(len(PERIODS)/2) - Load[e,g,c,d],
                    f"dayDeviationNegative_{e}_{g}_{c}_{d}"
                )

                for p in PERIODS:
                    
                    # the first period is less than all day periods
                    model += (
                        FP[e,g,c,d] <= p + PERIODS[-1]*(1 - BP[e,g,c,d,p]),
                        f"FirstPeriodMin_{e}_{g}_{c}_{d}_{p}"
                    )

                    # the last period is greater than all day periods
                    model += (
                        LP[e,g,c,d] >= BP[e,g,c,d,p] * p,
                        f"LastPeriodMax_{e}_{g}_{c}_{d}_{p}"
                    )

                # to ensure that the last period will equal 0 if the day is not studied 
                # and will be less than largest period if the day is studied
                model += (
                    LP[e,g,c,d] <= BD[e,g,c,d] * len(PERIODS),
                    f"LastPeriodMin_{e}_{g}_{c}_{d}_{p}"
                )

                # to ensure that the first period will always equal 0
                model += (
                    FP[e,g,c,d] <= BD[e,g,c,d] * len(PERIODS),
                    f"FirstPeriodMax_{e}_{g}_{c}_{d}"
                )

# === Objective ===
model += (
    pulp.lpSum(.5 * DEV[e,g,c,d] + 2 * BD[e,g,c,d] + 2 * (LP[e,g,c,d] - FP[e,g,c,d] + 1 - Load[e,g,c,d]) for e in environments for g in groups[e] for c in classes[g] for d in DAYS)
    - pulp.lpSum( pulp.lpSum( J[a,e,g,c,s,d,p] * AT[a][d][p] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e]) for a in A for d in DAYS for p in PERIODS)
    - pulp.lpSum( pulp.lpSum( I[t,e,g,c,s,d,p] * TT[t][d][p] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e]) for t in T for d in DAYS for p in PERIODS)
    - pulp.lpSum(ADS[a,s] * AS[a][s] for a in A for s in subj_list)
    - pulp.lpSum(TDS[t,s] * TS[t][s] for t in T for s in subj_list)
    , "MinimizeStudyDays"
)


# === Solve ===
# model.solve(pulp.PULP_CBC_CMD(msg=1))
model.solve(pulp.PULP_CBC_CMD(msg=True, timeLimit=10))  # Limit to 30 seconds

# === Results ===
print("Status:", pulp.LpStatus[model.status])

##################################################################

def draw_schedule(group, class_name, environment, path):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_axis_off()

    # Table setup
    cell_text = []
    cell_colors = []

    for d in DAYS:
        row_text = []
        row_colors = []

        for p in PERIODS:
            lecture_found = False
            section_found = False
            subjects_str = ""

            for s in subjects[environment]:
                val_lecture = pulp.value(Y[environment, group, class_name, s, d, p])
                val_section = pulp.value(X[environment, group, class_name, s, d, p])

                if val_lecture and val_lecture > 0.5:
                    lecture_found = True
                    subjects_str += f"Lec: {s}\n"
                if val_section and val_section > 0.5:
                    section_found = True
                    subjects_str += f"Sec: {s}\n"

            row_text.append(subjects_str.strip())

            if lecture_found:
                row_colors.append("lightblue")
            elif section_found:
                row_colors.append("lightgreen")
            else:
                row_colors.append("whitesmoke")

        cell_text.append(row_text)
        cell_colors.append(row_colors)

    # Create the table
    table = ax.table(cellText=cell_text,
                    cellColours=cell_colors,
                    colLabels=[f"P{p}" for p in PERIODS],
                    rowLabels=[f"Day {d}" for d in DAYS],
                    cellLoc='center',
                    loc='center')

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.2)

    plt.title(f"Schedule for {group} - {class_name}", fontsize=14)
    plt.tight_layout()
    img_path = os.path.join(path, f"{group}_{class_name}_{environment}.png")
    plt.savefig(img_path)
    plt.close(fig)  


# print schedule for year1 groups
os.makedirs("schedule", exist_ok=True)
for e in environments:
    env_dir = os.path.join("schedule", e)
    os.makedirs(env_dir, exist_ok=True)  # Create subfolder for environment

    for g in groups[e]:
        group_dir = os.path.join(env_dir, g)
        os.makedirs(group_dir, exist_ok=True)  # Create subfolder for group

        for c in classes[g]:
            draw_schedule(g, c, e, group_dir)
           


##################################################################3



