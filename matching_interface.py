# matching.py 
import csv
import pandas as pd
from openpyxl import Workbook
import pulp
from pulp import LpVariable, LpBinary, LpMinimize, LpProblem, lpSum, LpStatus

def parse_quota(quota_str):
    """Parse quota string into (min, max) tuple. Handles single numbers and ranges."""
    if '-' in quota_str:
        min_q, max_q = quota_str.split('-')
        return (0, int(max_q))
    return (0, int(quota_str))

def load_projects(csv_path):
    projects = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            project_id = row['ID'].strip()
            projects[project_id] = {
                'name': row['Projects'].strip(),
                'quota': parse_quota(row['Quotas'].strip())
            }
    return projects

def load_students(csv_path):
    students = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)  # Skip header
        for idx, row in enumerate(reader, start=1):
            name = row[0].strip()
            choices = [c.strip() for c in row[2:] if c.strip() not in ('-', '')]
            students.append({'id': idx, 'name': name, 'choices': choices})
    return students

def run_matching(project_path, student_path, output_path):

    projects = load_projects(project_path)
    students = load_students(student_path)
    
    for s in students:
        s['ranks'] = {p: i+1 for i, p in enumerate(s['choices'])}
    

    prob = LpProblem("StudentProjectAllocation", LpMinimize)
    x = {}
    z = LpVariable("z", lowBound=1, cat='Integer')
    
    for s in students:
        for p in s['choices']:
            x[(s['id'], p)] = LpVariable(f"x_{s['id']}_{p}", cat=LpBinary)
    
    for s in students:
        prob += lpSum(x[(s['id'], p)] for p in s['choices']) == 1
    
    for p_id, p_data in projects.items():
        _, max_q = p_data['quota']
        prob += lpSum(
            x[(s['id'], p_id)] 
            for s in students 
            if p_id in s['choices']
        ) <= max_q
    
    for s in students:
        prob += z >= lpSum(
            s['ranks'][p] * x[(s['id'], p)] 
            for p in s['choices']
        )
    
    total_rank = lpSum(
        s['ranks'][p] * x[(s['id'], p)] 
        for s in students 
        for p in s['choices']
    )
    prob += z * 1000 + total_rank
    
    # Solve problem
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    # Prepare results
    wb = Workbook()
    ws = wb.active
    ws.title = "Assignments"
    ws.append(["Student", "Assigned Project", "Rank"])
    
    rank_counts = {}
    assigned_count = 0
    
    # Record assignments
    for s in students:
        assigned = False
        for p in s['choices']:
            if x[(s['id'], p)].value() == 1:
                rank = s['ranks'][p]
                ws.append([s['name'], projects[p]['name'], rank])
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
                assigned_count += 1
                assigned = True
                break
        
        if not assigned:
            ws.append([s['name'], "NOT ASSIGNED", "—"])
    
    wb.save(output_path)
    
    return pd.read_excel(output_path)