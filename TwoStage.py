import gurobipy as gp
from gurobipy import GRB
import sys
from pprint import pprint
import itertools
import pandas as pd                # use DataFrame
import time                        # caculate time spend
import matplotlib.pyplot as plt    # draw the plot

# Parameter
import dataloader

class TwoStage:
    def __init__(self, data):
        self.data = data

    def stage_1(self):
        m = gp.Model("assignment")
        # Variable
        x = m.addVars(len(self.data.schedules), name="x", vtype=GRB.INTEGER) # number of worker work on schedule i (integer)
        y = m.addVars(len(self.data.scenarios), len(self.data.jobs), len(self.data.periods), name="y", vtype=GRB.INTEGER) # number of worker work on job j on period t (integer)
        z = m.addVars(len(self.data.scenarios), len(self.data.jobs), len(self.data.periods), name="z") # number of changes in job j at the start of period t(integer)
        l = m.addVars(len(self.data.scenarios), len(self.data.jobs), len(self.data.periods), name="l", vtype=GRB.INTEGER) # number of outsourcing worker on job j, period t (integer)

        # Model
        m.addConstrs(
            ((gp.quicksum(y[s, j, t] for j in self.data.jobs) == gp.quicksum(x[i] * self.data.schedulesIncludePeriods[i][t] for i in range(len(self.data.schedules))))\
            for t in self.data.periods for s in self.data.scenarios), name='分配到工作的人數要符合上班人數') # 分配到工作的人數要符合上班人數
        m.addConstrs((y[s, j, t] + l[s, j, t] >= self.data.demands[s][j][t] for j in self.data.jobs for t in self.data.periods for s in self.data.scenarios), name="值班人數要滿足需求") # 值班人數要滿足需求
        m.addConstrs((y[s, j, t] <= self.data.workerNumWithJobSkills[j] for j in self.data.jobs for t in self.data.periods for s in self.data.scenarios), name="任一時段，每個技能的值班人數 <= 總持有技能人數") # 任一時段，每個技能的值班人數 <= 總持有技能人數
        m.addConstrs((l[s, j, t] <= self.data.outsourcingLimit[j][t] for j in self.data.jobs for t in self.data.periods for s in self.data.scenarios), name="任一時段，每個外包人數 <= 可用外包人數") # 任一時段，每個外包人數 <= 可用外包人數
        m.addConstr((gp.quicksum(x[i] for i in range(len(self.data.schedules))) <= sum(self.data.workerNumWithJobSkills) - self.data.workerNumWithBothSkills), name="總上班人數 <= 總員工數") # 總上班人數 <= 總員工數
        m.addConstrs(
            (z[s, j, t] >= y[s, j, t] - y[s, j, t - 1] \
            for j in self.data.jobs for t in range(1, len(self.data.periods)) for s in self.data.scenarios), name='中途轉換次數(取絕對值)_1') # 中途轉換次數(取絕對值)
        m.addConstrs(
            (z[s, j, t] >= y[s, j, t - 1] - y[s, j, t] \
            for j in self.data.jobs for t in range(1, len(self.data.periods)) for s in self.data.scenarios), name='中途轉換次數(取絕對值)_2') # 中途轉換次數(取絕對值)

        # Objective Function
        cost = m.addVar(name="Cost")
        m.addConstr(cost ==\
            gp.quicksum(x[i] * self.data.schedulesIncludePeriods[i][t] * self.data.costOfHiring[t] for i in range(len(self.data.schedules)) for t in self.data.periods) + \
            gp.quicksum((
                gp.quicksum(z[s, j, t] for j in self.data.jobs for t in self.data.periods) * self.data.costOfSwitching +
                gp.quicksum(l[s, j, t] * self.data.costOfOutsourcing[j][t] for j in self.data.jobs for t in self.data.periods)
            ) * self.data.scenarioProbabilities[s] for s in self.data.scenarios))

        m.setObjective(cost, GRB.MINIMIZE)
            
        # Optimize
        m.optimize()
        status = m.status
        if status == GRB.UNBOUNDED:
            raise Exception("Unbounded")
        elif status == GRB.OPTIMAL:
            #print('The optimal objective is %g' % m.objVal)
            return {
                "x": [ x[i].x for i in range(len(self.data.schedules))],
                #"y": [[[ y[s, j, t].x for t in periods] for j in jobs ] for s in scenarios],
                "l": [[[ l[s, j, t].x for t in self.data.periods] for j in self.data.jobs ] for s in self.data.scenarios],
                "Cost": cost.x
            }
        elif status == GRB.INFEASIBLE:
            raise Exception(f'Infeasible')
        else:
            raise Exception(f'Optimization was stopped with status {status}')
        return False


    def stage_2(self, scenario, x):
        m = gp.Model("assignment")
        # Variable
        y = m.addVars(len(self.data.jobs), len(self.data.periods), name="y", vtype=GRB.INTEGER) # number of worker work on job j on period t (integer)
        z = m.addVars(len(self.data.jobs), len(self.data.periods), name="z") # number of changes in job j at the start of period t(integer)
        l = m.addVars(len(self.data.jobs), len(self.data.periods), name="l", vtype=GRB.INTEGER) # number of outsourcing worker on job j, period t (integer)

        # Model
        m.addConstrs(
            ((gp.quicksum(y[j, t] for j in self.data.jobs) == gp.quicksum(x[i] * self.data.schedulesIncludePeriods[i][t] for i in range(len(self.data.schedules))))\
            for t in self.data.periods), name='分配到工作的人數要符合上班人數') # 分配到工作的人數要符合上班人數
        m.addConstrs((y[j, t] + l[j, t] >= self.data.demands[scenario][j][t] for j in self.data.jobs for t in self.data.periods), name="值班人數要滿足需求") # 值班人數要滿足需求
        m.addConstrs((y[j, t] <= self.data.workerNumWithJobSkills[j] for j in self.data.jobs for t in self.data.periods), name="任一時段，每個技能的值班人數 <= 總持有技能人數") # 任一時段，每個技能的值班人數 <= 總持有技能人數
        m.addConstrs((l[j, t] <= self.data.outsourcingLimit[j][t] for j in self.data.jobs for t in self.data.periods), name="任一時段，每個外包人數 <= 可用外包人數") # 任一時段，每個外包人數 <= 可用外包人數
        m.addConstr((gp.quicksum(x[i] for i in range(len(self.data.schedules))) <= sum(self.data.workerNumWithJobSkills) - self.data.workerNumWithBothSkills), name="總上班人數 <= 總員工數") # 總上班人數 <= 總員工數
        m.addConstrs(
            (z[j, t] >= y[j, t] - y[j, t - 1] \
            for j in self.data.jobs for t in range(1, len(self.data.periods))), name='中途轉換次數(取絕對值)_1') # 中途轉換次數(取絕對值)
        m.addConstrs(
            (z[j, t] >= y[j, t - 1] - y[j, t] \
            for j in self.data.jobs for t in range(1, len(self.data.periods))), name='中途轉換次數(取絕對值)_2') # 中途轉換次數(取絕對值)

        # Objective Function
        cost = m.addVar(name="Cost")
        m.addConstr(cost == \
            gp.quicksum(x[i] * self.data.schedulesIncludePeriods[i][t] * self.data.costOfHiring[t] for i in range(len(self.data.schedules)) for t in self.data.periods) + 
            gp.quicksum(z[j, t] for j in self.data.jobs for t in self.data.periods) * self.data.costOfSwitching +
            gp.quicksum(l[j, t] * self.data.costOfOutsourcing[j][t] for j in self.data.jobs for t in self.data.periods)
        )
        m.setObjective(cost, GRB.MINIMIZE)
        
        # Optimize
        m.optimize()
        status = m.status
        if status == GRB.UNBOUNDED:
            # print(f"{scenario=}, {x=}, {objfunc=}, {epsilon=}")
            raise Exception("Unbounded")
        elif status == GRB.OPTIMAL:
            return {
                "Cost": cost.x,
                "l": sum([l[j, t].x for j in self.data.jobs for t in self.data.periods]),
                "x": x,
                "z": sum([z[j, t].x for j in self.data.jobs for t in self.data.periods])
            }
        elif status == GRB.INFEASIBLE:
            # print(f"{scenario=}, {x=}, {objfunc=}, {epsilon=}")
            raise Exception(f'Infeasible')
        else:
            # print(f"{scenario=}, {x=}, {objfunc=}, {epsilon=}")
            raise Exception(f'Optimization was stopped with status {status}')
        return False

    def drive(self, epsilon_r=3, scenario=None):
        # Stage 1
        stage_1_result = self.stage_1()

        # Stage 2
        solutions = dict()

        # for each scenario, caculate stage-2
        for scenario in (self.data.scenarios if scenario is None else [scenario]):
            solutions[scenario] = self.stage_2(scenario, stage_1_result['x'])

        return solutions

"""
if __name__ == '__main__':
    data = dataloader.generate_data()
    two_stage_model = TwoStage(data)
    print(data.demands)
    pprint(two_stage_model.drive())
"""
import numpy as np
if __name__ == '__main__':
    results = list()
    for i in range(100):
        data = dataloader.generate_data(do_random=True)
        two_stage_model = TwoStage(data)
        results.append(two_stage_model.drive())
    total_results = dict()
    for i in range(3):
        total_results[i] = {
            'Cost': np.mean([result[i]['Cost'] for result in results]), 
            'l': np.mean([result[i]['l'] for result in results])
        }

    print(total_results)
