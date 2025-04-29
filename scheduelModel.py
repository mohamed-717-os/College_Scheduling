import pulp
import os
import math

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json

    # /////////////////////  Data //////////////////////

def scheduelModel():
    with open('inputs/scheduling_inputs.json') as f:
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

    # ---------------------------------------

    # # Assistant subject Load 
    # for a in A:
    #     model += (
    #         pulp.lpSum(ADS[a,s] for s in subj_list) <= AL[1],
    #         f"AssistantLoadSubject_{a}"
    #     )

    # # Doctor subject Load 
    # for t in T:
    #     model += (
    #         pulp.lpSum(TDS[t,s] for s in subj_list) <= TL[1],
    #         f"DoctorLoadSubject_{t}"
    #     )

    # Assistant period Load per week
    # for a in A:
    #     model += (
    #         pulp.lpSum(J[a,e,g,c,s,d,p] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e] for d in DAYS for p in PERIODS) <= AL[0],
    #         f"AssistantLoad_{a}"
    #     )

    # # Doctor period Load per week
    # for t in T:
    #     model += (
    #         pulp.lpSum(I[t,e,g,c,s,d,p] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e] for d in DAYS for p in PERIODS) <= TL[0],
    #         f"DoctorLoad_{t}"
    #     )

    # ---------------------------------------

    # # Each lecture must be assigned to exactly one Doctor
    # for e in environments:
    #     for g in groups[e]:
    #         # Lecture is per group, assign based on the first class representation
    #         c0 = classes[g][0]
    #         for s in subjects[e]:
    #             for d in DAYS:
    #                 for p in PERIODS:
    #                      # If a lecture is scheduled...
    #                      model += (pulp.lpSum(I[t, e, g, c0, s, d, p] for t in T) == Y[e, g, c0, s, d, p],
    #                                f"AssignDoctorToLecture_{e}_{g}_{s}_{d}_{p}")

    # Each section must be assigned to exactly one Assistant
    # for e in environments:
    #     for g in groups[e]:
    #         for c in classes[g]:
    #             for s in subjects[e]:
    #                 for d in DAYS:
    #                     for p in PERIODS:
    #                         # If a section is scheduled...
    #                         model += (pulp.lpSum(J[a, e, g, c, s, d, p] for a in A) == X[e, g, c, s, d, p],
    #                                   f"AssignTAToSection_{e}_{g}_{c}_{s}_{d}_{p}")

    # for a in A:
    #     for s in subj_list:
    #         model += (
    #             pulp.lpSum(J[a, e, g, c, s, d, p]
    #                        for e in environments
    #                        for g in groups[e]
    #                        for c in classes[g]
    #                        for d in DAYS
    #                        for p in PERIODS)
    #             <= ADS[a, s] * AL[0],
    #             f"LinkADS_ub_{a}_{s}"
    #         )
    #         model += (
    #             pulp.lpSum(J[a, e, g, c, s, d, p]
    #                        for e in environments
    #                        for g in groups[e]
    #                        for c in classes[g]
    #                        for d in DAYS
    #                        for p in PERIODS)
    #             >= ADS[a, s],
    #             f"LinkADS_lb_{a}_{s}"
    #         )  

    # for a in A:
    #     for d in DAYS:
    #         for p in PERIODS:
    #             model += (
    #                 pulp.lpSum(J[a, e, g, c, s, d, p] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e]) <= 1,
    #                 f"AssignTAToSection_{a}_{d}_{p}"
    #             )

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
        pulp.lpSum(3 * DEV[e,g,c,d] +  70 * BD[e,g,c,d] +  10 * GAP[e,g,c,d] for e in environments for g in groups[e] for c in classes[g] for d in DAYS)
        # - pulp.lpSum( pulp.lpSum( J[a,e,g,c,s,d,p] * AT[a][str(d)][str(p)] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e]) for a in A for d in DAYS for p in PERIODS)
        # - pulp.lpSum( pulp.lpSum( I[t,e,g,c,s,d,p] * TT[t][str(d)][str(p)] for e in environments for g in groups[e] for c in classes[g] for s in subjects[e]) for t in T for d in DAYS for p in PERIODS)
        # - pulp.lpSum(ADS[a,s] * AS[a][s] for a in A for s in subj_list)
        # - pulp.lpSum(TDS[t,s] * TS[t][s] for t in T for s in subj_list)
        , "MinimizeStudyDays"
    )


    # === Solve ===
    # model.solve(pulp.PULP_CBC_CMD(msg=1))
    model.solve(pulp.PULP_CBC_CMD(msg=True, timeLimit=3))  # Limit to 30 seconds

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
                        # for a in A:
                        # if pulp.value(J[a,environment, group, class_name, s, d, p]):
                        subjects_str += f"Lec: {s}"

                    if val_section and val_section > 0.5:
                        section_found = True
                        # for t in T:
                        # if pulp.value(I[t,environment, group, class_name, s, d, p]):
                        subjects_str += f"Sec: {s}"

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
                    print(f'{g}{c} {d} gap = {pulp.value(GAP[e,g,c,d])} = {pulp.value(LP[e,g,c,d])} - {pulp.value(FP[e,g,c,d])} + 1 - {pulp.value(Load[e,g,c,d])}')
                    print(f'{g}{c} {d} DEV = {pulp.value(DEV[e,g,c,d])} > {pulp.value(Load[e,g,c,d])} - {math.ceil(len(PERIODS)/2)} - {math.ceil(len(PERIODS)/2)}*(1 - {pulp.value(BD[e,g,c,d])})')
                    print(f'{g}{c} {d} BD = {pulp.value(BD[e,g,c,d])}\n')
                print()
            print()
        print('--------------------------------')



    print(f'\nall gaps: {gaps}')
    print(f'\nall days: {days}')
    print('\nLecture\n')

    print('   ', ''.join(f'{p:^5} ' for p in PERIODS))

    for d in DAYS:
        print('d1: ', end='')
        for p in PERIODS:
            periodSub = 0
            for e in environments:
                for g in groups[e]:
                    for s in subjects[e]:
                        periodSub += pulp.value(Y[e,g,classes[g][0],s,d,p])
            print(f'{periodSub:^5} ', end='')
        print()

    print('\nSection\n')
    for d in DAYS:
        print('d1: ', end='')
        for p in PERIODS:
            periodSub = 0
            for e in environments:
                for g in groups[e]:
                    for c in classes[g]:
                        for s in subjects[e]:
                            periodSub += pulp.value(X[e,g,c,s,d,p])
            print(f'{periodSub:^5} ', end='')
        print()
