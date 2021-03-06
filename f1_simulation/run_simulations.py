import pandas as pd
from f1_racer import F1Racer
from simulation import simulate_race
from dataprocessing import F1Dataset
import numpy as np
from timeit import default_timer
from tqdm import tqdm

data = F1Dataset('data')


from overtaking import process_overtaking_data

overtaking_data = process_overtaking_data()


# Need to get the circuit ID of the courses
df = data.results.join(data.races.set_index('raceId'), on='raceId', rsuffix='_race')
df = (df.set_index(['raceId', 'driverId'])
        .join(data.qualifying
                  .set_index(['raceId', 'driverId'])[['q1', 'q2', 'q3']]
                  .replace('\\N', np.nan)
                  .apply(pd.to_datetime, format='%M:%S.%f')
                  .min(axis=1)
                  .rename('top_quali')))  # Yikes

df['top_quali'] = df['top_quali'] - pd.to_datetime('1900-01-01', format='%Y-%m-%d')
df.reset_index(drop=False, inplace=True)

df = df.loc[df['raceId'] >= 841]  # data where there is proper logging of pit stopping

races = df['raceId'].unique()

with open('results.csv', 'w') as f:
    f.write('race_id,driver,constructor,course,current_time,year,laps_since_pit_stop,lap_no,overtaking_mode,pit_stopping,pit_stop_duration,sampled_lap_time')

for race_id in tqdm(races):
    race = df.loc[df['raceId'] == race_id]

    assert len(race['circuitId'].unique()) == 1
    course_id = race['circuitId'].unique()[0]

    drivers = race['driverId'].tolist()
    constructors = race['constructorId'].tolist()
    year = data.races.loc[data.races['raceId'] == race_id, 'year'].values[0]
    num_laps = race['laps'].max()

    delay = np.timedelta64(0, 's')
    racers = []
    try:
        for driver_id, constructor_id in zip(drivers, constructors):
            # print(f"Simulating {driver_id=}, {constructor_id=}")
            top_quali = race.loc[race['driverId'] == driver_id, 'top_quali'].values[0]
            racer = F1Racer(race_id, driver_id, constructor_id, course_id, year, starting_time=delay, total_laps=num_laps, top_quali=top_quali, overtaking_data=overtaking_data)
            delay += np.timedelta64(1, 's')
            racers.append(racer)
    except Exception as e:
        print(f"Couldn't simulate race {race_id} because of error")
        continue

    try:
        simulate_race(racers, num_laps)
    except Exception as e:
        print(f"Couldn't simulate race {race_id} because of error")
    
