import pandas as pd
import numpy as np
from icecream import ic

# Load type data from CSV
type_chart = pd.read_csv('./prompts/type_chart.csv')

def defensive_type_matchup(types):
    type_1 = types[0]
    type_2 = types[1]

    matchup = {
        '4x' : [],
        '2x' : [],
        '1x' : [],
        '0.5x' : [],
        '0.25x' : [],
        '0x' : []
    }

    # Get type 1 column
    t1_m = type_chart.loc[:,type_1.title()].to_list()

    # Get type 2 column
    if type_2:
        t2_m = type_chart.loc[:,type_2.title()].to_list()
    else:
        t2_m = np.ones(len(t1_m))
    
    # Calculate the matchup
    m = [a * b for a, b in zip(t1_m, t2_m)]

    # Categorize the matchup
    for i in range(len(m)):
        if m[i] == 4:
            matchup['4x'].append(type_chart.iloc[i,0].upper())
        elif m[i] == 2:
            matchup['2x'].append(type_chart.iloc[i,0].upper())
        elif m[i] == 1:
            matchup['1x'].append(type_chart.iloc[i,0].upper())
        elif m[i] == 0.5:
            matchup['0.5x'].append(type_chart.iloc[i,0].upper())
        elif m[i] == 0.25:
            matchup['0.25x'].append(type_chart.iloc[i,0].upper())
        elif m[i] == 0:
            matchup['0x'].append(type_chart.iloc[i,0].upper())

    return matchup

def offensive_type_matchup(types):
    type_1 = types[0]
    type_2 = types[1]

    t1_matchup = {
        '2x' : [],
        '1x' : [],
        '0.5x' : [],
        '0x' : []
    }

    t2_matchup = {
        '2x' : [],
        '1x' : [],
        '0.5x' : [],
        '0x' : []
    }

    # Get type 1 matchups
    t1_m = type_chart.loc[type_chart['Attacking']==type_1.title(), :]
    t1_m = t1_m.iloc[0,1:].to_list()
    for i in range(len(t1_m)):
        if t1_m[i] == 2:
            t1_matchup['2x'].append(type_chart.iloc[i,0].upper())
        elif t1_m[i] == 1:
            t1_matchup['1x'].append(type_chart.iloc[i,0].upper())
        elif t1_m[i] == 0.5:
            t1_matchup['0.5x'].append(type_chart.iloc[i,0].upper())
        elif t1_m[i] == 0:
            t1_matchup['0x'].append(type_chart.iloc[i,0].upper())

    # Get type 2 matchups
    if type_2:
        t2_m = type_chart.loc[type_chart['Attacking']==type_2.title(), :]
        t2_m = t2_m.iloc[0,1:].to_list()
        for i in range(len(t2_m)):
            if t2_m[i] == 2:
                t2_matchup['2x'].append(type_chart.iloc[i,0].upper())
            elif t2_m[i] == 1:
                t2_matchup['1x'].append(type_chart.iloc[i,0].upper())
            elif t2_m[i] == 0.5:
                t2_matchup['0.5x'].append(type_chart.iloc[i,0].upper())
            elif t2_m[i] == 0:
                t2_matchup['0x'].append(type_chart.iloc[i,0].upper())
    else:
        t2_matchup = None

    return t1_matchup, t2_matchup

def type_test():
    types = ['ROCK', 'GROUND']
    def_matchups = defensive_type_matchup(types)
    ic(def_matchups)

    off_matchups = offensive_type_matchup(types)
    ic(off_matchups)

if __name__ == "__main__":
    type_test()