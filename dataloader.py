from scipy.stats import norm
import random
import numpy as np
from pprint import pprint

class TestData():
    pass

def demand_generation_normal(length, offset=0, do_random=False):
    a = np.roll(np.array(range(0, length)) - length // 2, offset if not do_random else int(random.uniform(-length // 2, length // 2))) 
    a = a / ( random.uniform(3, 9) if do_random else 6 )
    return (norm().pdf(a) * ( random.uniform(60, 140) if do_random else 100 )).astype(int)

def generate_data(do_random=False):
    data = TestData()

    data.jobs = list(range(0, 2))
    data.scenarios = list(range(0, 3))
    data.scenarioProbabilities = [ random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1) ]
    data.scenarioProbabilities = [ r / sum(data.scenarioProbabilities) for r in data.scenarioProbabilities ]
    data.periods = list(range(0, 24))
    data.demands = [[ demand_generation_normal(len(data.periods), offset=s * (j * 2 - 1) * 4 ,do_random=do_random) * (s + 1) // (4 + j) for j in data.jobs ] for s in data.scenarios ] # demand of worker needed on job j at period t in scenario s
    data.schedules = [(0, 6), (3, 9), (6, 12), (9, 15), (12, 18), (15, 21), (18, 24), (21, 3)]
    data.schedulesIncludePeriods = [
        [ ( 1 if i[0] <= t < i[1] else 0 ) if i[0] <= i[1] else ( 1 if i[0] <= t or t < i[1] else 0 ) for t in data.periods ] for i in data.schedules
    ] # schedule i include period t or not (binary)
    data.workerNumWithJobSkills = [ 90 for j in data.jobs ] # number of workers who have the skill for job j
    data.workerNumWithBothSkills = 30 # number of workers who have both skills
    data.costOfHiring = [10 for i in data.periods] # cost of hiring a worker to work at period t
    data.costOfSwitching = 5 # cost of letting a worker change jobs at the middle of a day
    data.costOfOutsourcing = [[ 100 for t in data.periods ] for j in data.jobs] # Cost of satisfied an unit of demand by outsourcing for job j on period t
    data.outsourcingLimit = [[ 10 for t in data.periods ] for j in data.jobs] # numbers on outsourcing workers for job j on period t

    #print("demands:")
    #pprint(data.demands)

    return data