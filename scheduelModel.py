import pulp
import os
import math

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json

    # /////////////////////  Data //////////////////////

def scheduelModel():

    with open('scheduling_inputs01.json') as f:
        data = json.load(f)

        HALLS = data['halls']  # number of halls
        LABS  = data['labs']   # number of labs
        DAYS    = list(range(1,data['days'] + 1))  # 1..5
        PERIODS = list(range(1,data['periods'] + 1))  # 1..5

            # ------------------------------------------- #

        environments = data['environments']

        groups = data['groups']

        classes = data['classes']

        subjects = data['subjects']

        subj_list = {s for e in environments for s in subjects[e]}
        subj_list = list(subj_list)
            # ------------------------------------------- #

        A = data['A']
        T = data['T']

        AL = data['AL']   # maximum load for assistant (periods per week, subjects)
        TL = data['TL']  # maximum load for Doctor (periods per week, subjects)


        # AT[a][d][p] = 1 if TL a prefers time (d,p), else 0
        AT = data['AT']
        TT = data['TT']

        # AS[a][s] = 1 if TL a want to teach subject s, else 0
        AS = data['AS']
        TS = data['TS']

            
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
        "AssistantSubject",
        [(a,s)
        for a in A
        for s in subj_list],
        cat='Binary'
    )

    TDS = pulp.LpVariable.dicts(
        "DoctorSubject",
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

    GAP = pulp.LpVariable.dicts(
        "dayGap",
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

    # All classes of the same group takes the lecture together
            for s in subjects[e]:
                for d in DAYS:
                    for p in PERIODS:
                        model += (           # if the first class takes the lecture, all classes of the same group takes the lecture together
                            pulp.lpSum(Y[e,g,c,s,d,p] for c in classes[g]) == (len(classes[g]) * Y[e,g, classes[g][0] ,s,d,p]),
                            f"GroupClass_{e}_{g}_{s}_{d}_{p}"
                        )

                        for t in T:
                            model += (
                                pulp.lpSum(I[t,e,g,c,s,d,p] for c in classes[g]) == (len(classes[g]) * I[t,e,g,classes[g][0],s,d,p]),
                                f"GroupDoctor_{t}_{e}_{g}_{s}_{d}_{p}"
                            )

    # ---------------------------------------

    # Assistant subject Load 
    for a in A:
        model += (
            pulp.lpSum(ADS[a,s] for s in subj_list) <= AL[1],
            f"AssistantLoadSubject_{a}"
        )

    # Doctor subject Load 
    for t in T:
        model += (
            pulp.lpSum(TDS[t,s] for s in subj_list) <= TL[1],
            f"DoctorLoadSubject_{t}"
        )

    # Assistant period Load per week
    for a in A:
        model += (
            pulp.lpSum(J[a,e,g,c,s,d,p] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e] for d in DAYS for p in PERIODS) <= AL[0],
            f"AssistantLoad_{a}"
        )

    # Doctor period Load per week
    for t in T:
        model += (
            pulp.lpSum(I[t,e,g,classes[g][0],s,d,p] for e in environments for g in groups[e] for s in subjects[e] for d in DAYS for p in PERIODS) <= TL[0],
            f"DoctorLoad_{t}"
        )

    # ---------------------------------------

    # Linking the doctors and assistants to the lectures and sections
    for e in environments:
        for g in groups[e]:
            for c in classes[g]:
                for s in subjects[e]:
                    for d in DAYS:
                        for p in PERIODS:
                            model += (pulp.lpSum(I[t, e, g, c, s, d, p] for t in T) == Y[e, g, c, s, d, p],
                                    f"AssignDoctorToLecture_{e}_{g}_{c}_{s}_{d}_{p}")

    for e in environments:
        for g in groups[e]:
            for c in classes[g]:
                for s in subjects[e]:
                    for d in DAYS:
                        for p in PERIODS:
                            model += (pulp.lpSum(J[a, e, g, c, s, d, p] for a in A) == X[e, g, c, s, d, p],
                                    f"AssignTAToSection_{e}_{g}_{c}_{s}_{d}_{p}")

    for s in subj_list:
        for a in A:
            model += (
                pulp.lpSum(J[a, e, g, c, s, d, p]
                        for e in environments
                        for g in groups[e]
                        for c in classes[g]
                        for d in DAYS
                        for p in PERIODS)
                <= ADS[a, s] * AL[0],
                f"LinkADS_ub_{a}_{s}"
            )
            model += (
                pulp.lpSum(J[a, e, g, c, s, d, p]
                        for e in environments
                        for g in groups[e]
                        for c in classes[g]
                        for d in DAYS
                        for p in PERIODS)
                >= ADS[a, s],
                f"LinkADS_lb_{a}_{s}"
            )  

        for t in T:
            model += (
                pulp.lpSum(I[t, e, g, classes[g][0], s, d, p]
                        for e in environments
                        for g in groups[e]
                        for d in DAYS
                        for p in PERIODS)
                <= TDS[t, s] * TL[0],
                f"LinkTDS_ub_{t}_{s}"
            )
            model += (
                pulp.lpSum(I[t, e, g, classes[g][0], s, d, p]
                        for e in environments
                        for g in groups[e]
                        for d in DAYS
                        for p in PERIODS)
                >= TDS[t, s],
                f"LinkTDS_lb_{t}_{s}"
            )  

    # assistants and doctors have just 1 subject in the single period
    for a in A:
        for d in DAYS:
            for p in PERIODS:
                model += (
                    pulp.lpSum(J[a, e, g, c, s, d, p] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e]) <= 1,
                    f"AssignTAToSection_{a}_{d}_{p}"
                )

    for t in T:
        for d in DAYS:
            for p in PERIODS:
                model += (
                    pulp.lpSum(I[t, e, g, classes[g][0], s, d, p] for e in environments for g in groups[e] for s in subjects[e]) <= 1,
                    f"AssignTAToLecture_{t}_{d}_{p}"
                )
    # ---------------------------------------
    for e in environments:
        for g in groups[e]:
            for c in classes[g]:
                for d in DAYS:

                    # Link study‐day indicator
                    for p in PERIODS:
                        
                        model += ( BP[e,g,c,d,p] ==
                            pulp.lpSum(X[e,g,c,s,d,p] for s in subjects[e]) +
                            pulp.lpSum(Y[e,g,c,s,d,p] for s in subjects[e])
                        )

                        model += (BP[e,g,c,d,p] <= 1 , f"NoDouble_{e}_{g}_{c}_{d}_{p}")


                    # day study periods for each section
                    model += (
                        pulp.lpSum(BP[e,g,c,d,p] for p in PERIODS) == Load[e,g,c,d],
                        f"dayLoad_{e}_{g}_{c}_{d}"
                    )

                    # If any session ⇒ z=1
                    model += (Load[e,g,c,d] >= BD[e,g,c,d], f"Zone_{e}_{g}_{c}_{d}")
                    # If no sessions ⇒ z=0
                    model += (Load[e,g,c,d] <= len(PERIODS) * BD[e,g,c,d], f"Zzero_{e}_{g}_{c}_{d}")

                    # achive mean load:     DEV >= | Load - len(PERIODS)/2 |
                    model += (
                        DEV[e,g,c,d] >= Load[e,g,c,d] - math.ceil(len(PERIODS)/2),
                        f"dayDeviationPositive_{e}_{g}_{c}_{d}"
                    )

                    model += (
                        DEV[e,g,c,d] >= BD[e,g,c,d] * (math.ceil(len(PERIODS)/2)) - Load[e,g,c,d],
                        f"dayDeviationNegative_{e}_{g}_{c}_{d}"
                    )
                    
                    model += (DEV[e,g,c,d] <= len(PERIODS) * BD[e,g,c,d], f"DevZeroIfFree_{e}_{g}_{c}_{d}")

                    # ---------------------------------------

                    # to ensure that the last period will equal 0 if the day is not studied 
                    # and will be less than largest period if the day is studied
                    model += (
                        LP[e,g,c,d] <= BD[e,g,c,d] * len(PERIODS),
                        f"LastPeriodMin_{e}_{g}_{c}_{d}"
                    )

                    # to ensure that the first period will always equal 0
                    model += (
                        FP[e,g,c,d] <= BD[e,g,c,d] * len(PERIODS),
                        f"FirstPeriodMax_{e}_{g}_{c}_{d}"
                    )

                    # calculate the gap between the first and last period
                    model += (
                        GAP[e,g,c,d] == LP[e,g,c,d] - FP[e,g,c,d] - Load[e,g,c,d] + BD[e,g,c,d],
                        f"Gap_{e}_{g}_{c}_{d}"
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



    
    # === Objective ===
    model += (
        pulp.lpSum( 9* DEV[e,g,c,d] +   25 * BD[e,g,c,d] +   30 * GAP[e,g,c,d] for e in environments for g in groups[e] for c in classes[g] for d in DAYS)
        - pulp.lpSum( pulp.lpSum( J[a,e,g,c,s,d,p] * AT[a][str(d)][str(p)] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e]) for a in A for d in DAYS for p in PERIODS)
        - pulp.lpSum( pulp.lpSum( I[t,e,g,c,s,d,p] * TT[t][str(d)][str(p)] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e]) for t in T for d in DAYS for p in PERIODS)
        - pulp.lpSum(ADS[a,s] * AS[a][s] for a in A for s in subj_list)
        - pulp.lpSum(TDS[t,s] * TS[t][s] for t in T for s in subj_list)
        , "MinimizeStudyDays"
    )


    # === Solve ===
    # model.solve(pulp.PULP_CBC_CMD(msg=1))
    model.solve(pulp.PULP_CBC_CMD(msg=True, timeLimit=120))  # Limit to 30 seconds

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
                        for t in T:
                            if pulp.value(I[t,environment, group, class_name, s, d, p]):
                                # print(f'{group}{class_name} {d} {p} Lec:{s}: {t}')
                                subjects_str += f"Lec:{s}: {t}"

                    if val_section and val_section > 0.5:
                        section_found = True
                        for a in A:
                            if pulp.value(J[a,environment, group, class_name, s, d, p]):
                                subjects_str += f"Sec:{s}: {a}"


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

    def Teacher_schedule(a, subj_list, path):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_axis_off()

        # Table setup
        cell_text = []
        cell_colors = []

        for d in DAYS:
            row_text = []
            row_colors = []

            for p in PERIODS:
                subjects_str = ""
                section_found = False
                
                for s in subj_list:
                    for e in environments:
                        for g in groups[e]: 
                            for c in classes[g]:
                                val_assistant = pulp.value(J[a, e, g, c, s, d, p])

                                if val_assistant and val_assistant > 0.5:
                                    subjects_str += f"sec:{c} - {s}"
                                    section_found = True


                row_text.append(subjects_str.strip())

                if section_found:
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
                        loc='center',)

        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.2)

        plt.title(f"Schedule for {a}", fontsize=14)
        plt.tight_layout()
        img_path = os.path.join(path, f"{a}.png")
        plt.savefig(img_path)
        plt.close(fig)  

    def Doctor_schedule(t, subj_list, path):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_axis_off()

        # Table setup
        cell_text = []
        cell_colors = []

        for d in DAYS:
            row_text = []
            row_colors = []

            for p in PERIODS:
                subjects_str = ""
                lecture_found = False
                
                for s in subj_list:
                    for e in environments:
                        for g in groups[e]: 
                            val_doctor = pulp.value(I[t, e, g, classes[g][0], s, d, p])

                            if val_doctor and val_doctor > 0.5:
                                subjects_str += f"group:{g} - {s}"
                                lecture_found = True


                row_text.append(subjects_str.strip())

                if lecture_found:
                    row_colors.append("lightblue")
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

        plt.title(f"Schedule for {t}", fontsize=14)
        plt.tight_layout()
        img_path = os.path.join(path, f"{t}.png")
        plt.savefig(img_path)
        plt.close(fig)  

    # print schedule for year1 groups
    os.makedirs("schedule", exist_ok=True)

    gaps = 0
    days = 0
    for e in environments:
        env_dir = os.path.join("schedule", e)
        os.makedirs(env_dir, exist_ok=True)  # Create subfolder for environment

        for g in groups[e]:
            group_dir = os.path.join(env_dir, g)
            os.makedirs(group_dir, exist_ok=True)  # Create subfolder for group

            for c in classes[g]:
                draw_schedule(g, c, e, group_dir)

                for d in DAYS:
                    gaps +=  pulp.value(GAP[e,g,c,d])
                    days += pulp.value(BD[e,g,c,d])

    assist_dir = os.path.join("schedule", 'assistants')
    for a in A:
        os.makedirs(assist_dir, exist_ok=True)  # Create subfolder for environment
        Teacher_schedule(a, subj_list, assist_dir)

    doc_dir = os.path.join("schedule", 'doctors')
    for t in T:
        os.makedirs(doc_dir, exist_ok=True)  # Create subfolder for environment
        Doctor_schedule(t, subj_list, doc_dir)
