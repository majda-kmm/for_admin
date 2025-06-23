# matching.py

import csv
import pandas as pd
from openpyxl import Workbook
import pulp
from pulp import LpVariable, LpBinary, LpMinimize, LpProblem, lpSum

def parse_quota(quota_str):
    return tuple(map(int, quota_str.split('-'))) if '-' in quota_str else (int(quota_str), int(quota_str))

def load_projects(csv_path):
    projects = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            project_id = row['ID'].strip()
            project_name = row['Projects'].strip()
            quota = parse_quota(row['Quotas'].strip())
            projects[project_id] = {'quota': quota, 'name': project_name}
    return projects

def load_students(csv_path):
    students = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)  # Skip header
        for idx, row in enumerate(reader, start=1):
            name = row[0].strip()
            # skip choices that are '_', keep others including empty ones
            choices = [choice.strip() for choice in row[2:] if choice.strip() != '-' and choice.strip() != '']
            students.append({'id': idx, 'name': name, 'choices': choices})
    return students

def run_matching(project_path, student_path, output_path):
    projects = load_projects(project_path)
    students = load_students(student_path)
    for s in students:
        s['ranks'] = {p: i+1 for i, p in enumerate(s['choices'])}

    prob = LpProblem("StudentProjectAllocation", LpMinimize)
    x = {(s['id'], p): LpVariable(f"x_{s['id']}_{p}", cat=LpBinary)
         for s in students for p in s['choices']}
    y = {p: LpVariable(f"y_{p}", cat=LpBinary) for p in projects}
    z = LpVariable("z", lowBound=1, cat='Integer')

    for s in students:
        prob += lpSum(x[(s['id'], p)] for p in s['choices']) == 1
    for p in projects:
        min_q, max_q = projects[p]['quota']
        total = lpSum(x[(s['id'], p)] for s in students if p in s['choices'])
        prob += total >= min_q * y[p]
        prob += total <= max_q * y[p]
    for s in students:
        prob += z >= lpSum(s['ranks'][p] * x[(s['id'], p)] for p in s['choices'])

    total_rank = lpSum(s['ranks'][p] * x[(s['id'], p)] for s in students for p in s['choices'])
    prob += z * 1000 + total_rank
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    wb = Workbook()
    ws = wb.active
    ws.title = "Assignments"
    ws.append(["Student", "Assigned Project", "Rank"])
    for s in students:
        for p in s['choices']:
            if x[(s['id'], p)].value() == 1:
                ws.append([s['name'], projects[p]['name'], s['ranks'][p]])
                break
    wb.save(output_path)
    return pd.read_excel(output_path)