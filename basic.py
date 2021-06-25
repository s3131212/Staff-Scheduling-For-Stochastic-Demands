import gurobipy as gp
from gurobipy import GRB
import sys
from pprint import pprint
import pandas as pd                # use DataFrame
import time                        # caculate time spend

# Parameter 
import dataloader

class Basic:
    def __init__(self, data):
        self.data = data
    def solve_model(self):
        m = gp.Model("basic")
        
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
            raise "Unbounded"
        elif status == GRB.OPTIMAL:
            return {
                "Cost": cost.x,
                "x": [ x[i].x for i in range(len(self.data.schedules))],
                "l": sum([l[s, j, t].x for j in self.data.jobs for t in self.data.periods for s in self.data.scenarios])
            }
        elif status != GRB.INF_OR_UNBD and status != GRB.INFEASIBLE:
            raise f'Optimization was stopped with status {status}'
    
    def drive(self):
        return self.solve_model()
"""
if __name__ == '__main__':
    data = dataloader.generate_data(do_random=False)
    basic_model = Basic(data)
    print(basic_model.drive())
"""

import numpy as np
if __name__ == '__main__':
    results = list()
    for i in range(100):
        data = dataloader.generate_data(do_random=True)
        basic_model = Basic(data)
        results.append(basic_model.drive())
    total_results = {
        'Cost': np.mean([result['Cost'] for result in results]), 
        'l': np.mean([result['l'] for result in results])
    }

    print(total_results)
