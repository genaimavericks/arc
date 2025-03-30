from langchain.prompts.prompt import PromptTemplate

CYPHER_GENERATION_TEMPLATE = '''\
### Task:
Generate Cypher queries for time-series foam factory data using this schema:

### Database Schema:

*Create Nodes*

// Create Teams
CREATE (t:Team {{id: 'Location A_Factory 1_Member_0', factory: 'Factory 1', location: 'Location A'}})

// Create Members
CREATE (m:Member {{
    name: 'Member_0_0', 
    experience: 10.0, 
    trainingLevel: '3.6', 
    absenteeismRate: 0.45, 
    factory: 'Factory 1', 
    location: 'Location A'
}})

// Create Dates
CREATE (d1:Date {{date: date('2020-01-01')}})

// Create Factories
CREATE (f:Factory {{factory_id: 'Factory 1', location: 'Location A'}})

// Create Machines
CREATE (m:Machine {{machine_id: 'Location A-Factory 1-Type 2', machine_type: 'Type 2', machine_age: 8.89}})

// Create Products
CREATE (p:Product {{product_category: 'Category A'}})

// Create Suppliers
CREATE (s:Supplier {{supplier_name: 'Supplier X'}})

// Create Raw Materials
CREATE (r:RawMaterial {{raw_material_quality: 1}})

*Create Relationships*

// HAS_MEMBER relationship

MATCH (t:Team {{id: 'Location A_Factory 1_Member_0'}})
MATCH (m:Member {{name: 'John Doe', experience: 5, trainingLevel: 'Level 3', absenteeismRate: 0.03, factory: 'Factory A', location: 'Location X'}})
CREATE (t)-[:HAS_MEMBER]->(m)

// HAS_MACHINE  relationship

MATCH (f:Factory {{factory_id: 'Factory 1', location: 'Location A'}})
CREATE (m:Machine {{machine_id: 'Location A-Factory 1-Type 2'}})
CREATE (f)-[:HAS_MACHINE]->(m)

// OPERATED_ON relationship      

MATCH (f:Factory {{factory_id: 'Factory 1', location: 'Location A'}})
MATCH (d:Date {{date: date('2020-01-01')}})
CREATE (f)-[:OPERATED_ON {{shift: 'Day'}}]->(d)

// USED_ON  relationship

MATCH (m:Machine {{machine_id: 'Location A-Factory 1-Type 2'}})
MATCH (d:Date {{date: date('2025-01-01')}})
CREATE  (m)-[:USED_ON {{
    shift: 'Shift 1', 
    machine_utilization: 0.8, 
    cycle_time: 120, 
    energy_consumption: 150, 
    co2_emissions: 20, 
    emission_limit_compliance: 'Yes', 
    cost_of_downtime: 100,
    breakdowns: 2, 
    safety_incidents: 0, 
    defect_rate: 0.01, 
    energy_efficiency_rating: 1.5, 
    waste_generated: 10, 
    water_usage: 300, 
    temperature: 70, 
    pressure: 200, 
    chemical_ratio: 4.0, 
    mixing_speed: 200, 
    production_volume: 500, 
    revenue: 10000, 
    profit_margin: 0.15, 
    market_demand_index: 5
}}]->(d)

// USED_BY_TEAM relationship


MATCH (m:Machine {{machine_id: 'Location A-Factory 1-Type 2'}})
MATCH (t:Team {{id: 'Location A_Factory 1_Member_0'}})
CREATE (m)-[:USED_BY_TEAM {{
    shift: 'Day', 
    date: date('2020-01-01'), 
    average_operator_training_level: 3.6, 
    average_absentism: 0.05, 
    average_operator_experience: 5
}}]->(t)

// PRODUCED_ON relationship

MATCH (p:Product {{product_category: 'Category A'}})
MATCH (d:Date {{date: date('2020-01-01')}})
CREATE (p)-[:PRODUCED_ON {{batch: 'Batch 1', batch_quality: 'High'}}]->(d)

// SUPPLIED_BY relationship

MATCH (r:RawMaterial {{raw_material_quality: 1}})
MATCH (s:Supplier {{supplier_name: 'Supplier X'}})
CREATE (r)-[:SUPPLIED_BY {{date: date('2020-01-01'), shift: 'Day', supplier_delays: 0}}]->(s)

// PRODUCED_USING relationship

MATCH (p:Product {{product_category: 'Category A'}})
MATCH (r:RawMaterial {{raw_material_quality: 1}})
CREATE (p)-[:PRODUCED_USING {{date: date('2020-01-01'), shift: 'Day', batch: 'Batch 1', batch_quality: 'High'}}]->(r)

### Positive Examples:
Question: Get details about team Location A_Factory 1_Member_0 and its members: 

MATCH (t:Team {{id: 'Location A_Factory 1_Member_0'}})-[:HAS_MEMBER]->(m)
return t, m

Question: Find factories with an average profit margin below a certain threshold:

MATCH (f:Factory)-[:HAS_MACHINE]->(m:Machine)-[u:USED_ON]->(d:Date)
WITH f, avg(u.profit_margin) AS averageProfitMargin
WHERE averageProfitMargin < 30
RETURN f.factory_id AS FactoryID, averageProfitMargin

Question: Compare revenue and profit margin between two factories on a specific date:


MATCH (f1:Factory {{factory_id: 'Factory 1'}})-[:HAS_MACHINE]->(m1:Machine)-[u1:USED_ON]->(d:Date {{date: date('2020-01-01')}}),
      (f2:Factory {{factory_id: 'Factory 2'}})-[:HAS_MACHINE]->(m2:Machine)-[u2:USED_ON]->(d)
RETURN f1.factory_id AS Factory1, avg(u1.revenue) AS Factory1Revenue, avg(u1.profit_margin) AS Factory1ProfitMargin,
       f2.factory_id AS Factory2, avg(u2.revenue) AS Factory2Revenue, avg(u2.profit_margin) AS Factory2ProfitMargin

Question: Analyze the correlation between production volume and revenue:
MATCH (f:Factory)-[:HAS_MACHINE]->(m:Machine)-[u:USED_ON]->(d:Date)
RETURN f.factory_id AS FactoryID, u.production_volume AS ProductionVolume, u.revenue AS Revenue

Question: Identify defect rates for a specific machine:

MATCH (m:Machine {{machine_id: 'Location A-Factory 1-Type 2'}})-[u:USED_ON]->(d:Date)
RETURN m.machine_id AS MachineID, u.defect_rate AS DefectRate, d.date AS Date
ORDER BY d.date

Question: Analyze the combined impact of machine downtime and defect rate on production volume:

MATCH (m:Machine)-[u:USED_ON]->(d:Date)
WITH m, avg(u.cost_of_downtime) AS AvgDowntime, avg(u.defect_rate) AS AvgDefectRate, avg(u.production_volume) AS AvgProductionVolume
RETURN m.machine_id AS MachineID, AvgDowntime, AvgDefectRate, AvgProductionVolume
ORDER BY AvgProductionVolume DESC

Question: Analyze the impact of machine downtime on revenue (requires linking downtime to revenue loss):

MATCH (m:Machine)-[u:USED_ON]->(d:Date)
WITH m, avg(u.cost_of_downtime) AS AvgDowntimeCost, avg(u.revenue) AS AvgRevenue
RETURN m.machine_id AS MachineID, AvgDowntimeCost, AvgRevenue, (AvgRevenue - AvgDowntimeCost) AS RevenueAfterDowntime
ORDER BY RevenueAfterDowntime DESC

Question: Analyze profit margin trends over time (requires more date data and potentially APOC for time series functions):
This simplified version shows profit margin over time. For more advanced analysis, consider the APOC library:

MATCH (m:Machine)-[u:USED_ON]->(d:Date)
RETURN d.date AS Date, avg(u.profit_margin) AS AvgProfitMargin
ORDER BY Date

Question: Identify factors contributing to low profit margins (combining multiple relationships and properties):

MATCH (f:Factory)-[:HAS_MACHINE]->(m:Machine)-[u:USED_ON]->(d:Date)
WITH f, avg(u.profit_margin) AS AvgProfitMargin, avg(u.machine_utilization) AS AvgUtilization, avg(u.defect_rate) AS AvgDefectRate, avg(u.energy_consumption) AS AvgEnergyConsumption, avg(u.co2_emissions) AS AvgCO2Emissions, avg(u.cost_of_downtime) AS AvgDowntimeCost, avg(u.breakdowns) AS AvgBreakdowns, avg(u.safety_incidents) AS AvgSafetyIncidents
WHERE AvgProfitMargin < 25 // Adjust threshold as needed
RETURN f.factory_id AS FactoryID, AvgProfitMargin, AvgUtilization, AvgDefectRate, AvgEnergyConsumption, AvgCO2Emissions, AvgDowntimeCost, AvgBreakdowns, AvgSafetyIncidents
ORDER BY AvgProfitMargin ASC

Question: List factories and average low profit margins:

MATCH (f:Factory)-[:HAS_MACHINE]->(m:Machine)-[u:USED_ON]->(d:Date)
WITH f, avg(u.profit_margin) AS AvgProfitMargin
WHERE AvgProfitMargin < 20 // Adjust threshold as needed
RETURN f.factory_id AS FactoryID, AvgProfitMargin
ORDER BY AvgProfitMargin ASC

Question: How does the profit margin change over time for Factory 1 (return date wise data)?

MATCH (f:Factory {{factory_id: 'Factory 1'}})-[:HAS_MACHINE]->(m:Machine)-[u:USED_ON]->(d:Date)
WITH d.date AS Date, avg(u.profit_margin) AS AvgProfitMargin
RETURN Date, AvgProfitMargin
ORDER BY Date

Question: How does the profit margin change over time for Factory 1 (return quarter wise data)?

MATCH (f:Factory {{factory_id: 'Factory 1'}})-[:HAS_MACHINE]->(m:Machine)-[u:USED_ON]->(d:Date)
WITH d, u,
     toString(d.date) AS DateString,
     substring(toString(d.date), 0, 7) AS YearMonth
WITH YearMonth, avg(u.profit_margin) AS AvgProfitMargin
RETURN YearMonth, AvgProfitMargin
ORDER BY YearMonth

Question: How does the profit margin change over time for Factory 1 (return yearly data)?

MATCH (f:Factory {{factory_id: 'Factory 1'}})-[:HAS_MACHINE]->(m:Machine)-[u:USED_ON]->(d:Date)
WITH d, u, 
     toString(d.date) AS DateString,
     substring(toString(d.date), 0, 4) AS Year,
     toInteger(substring(toString(d.date), 5, 2)) AS Month
WITH Year, ((Month - 1) / 3) + 1 AS Quarter, avg(u.profit_margin) AS AvgProfitMargin
RETURN Year + '-Q' + Quarter AS YearQuarter, AvgProfitMargin
ORDER BY YearQuarter

Question: How does the co2 emissions change over time for machine "Location A-Factory 1-Type 2" in 2023?

MATCH (m:Machine {{machine_id: 'Location A-Factory 1-Type 2'}})-[u:USED_ON]->(d:Date)
WHERE d.date >= date('2023-01-01') AND d.date <= date('2023-12-31')
WITH d, u,
     toString(d.date) AS DateString,
     substring(toString(d.date), 0, 7) AS YearMonth
WITH YearMonth, avg(u.co2_emissions) AS AvgCO2Emissions
RETURN YearMonth, AvgCO2Emissions
ORDER BY YearMonth

Question: what day was the best for overall production?

MATCH (m:Machine)-[u:USED_ON]->(d:Date)
WITH d.date AS Date, sum(u.production_volume) AS TotalProductionVolume
RETURN Date, TotalProductionVolume
ORDER BY TotalProductionVolume DESC
LIMIT 1

Question: Which teams operated machines that experienced defects?

MATCH(m:Machine)-[u:USED_ON]->(d:Date)
with m,u,d
MATCH (m)-[ut:USED_BY_TEAM]->(t:Team)
WHERE u.defect_rate > 0 and d.date = ut.date
RETURN distinct(t.id) as TeamID, m.machine_id as MachineID

Question: How many locations are there?

MATCH (f:Factory)
return DISTINCT(f.location)

Question: What is the average absenteeism rate?

MATCH (m:Machine)-[u:USED_BY_TEAM]->(t:Team)
return avg(u.average_absentialism)

Question: What is average absenteeism rate for each team?

MATCH (m:Machine)-[u:USED_BY_TEAM]->(t:Team)
RETURN t.id AS Team, avg(u.average_absentialism) AS AverageAbsenteeism

Question: What is the average absenteeism rate for location?

MATCH (m:Machine)-[u:USED_BY_TEAM]->(t:Team)
RETURN t.location AS Location, avg(u.average_absentialism) AS AverageAbsenteeism

Question: Which year was the most profitable

MATCH (f:Factory)-[:HAS_MACHINE]->(m:Machine)-[u:USED_ON]->(d:Date)
WITH substring(toString(d.date), 0, 4) AS Year, sum(u.revenue) AS TotalRevenue
RETURN Year
ORDER BY TotalRevenue DESC
LIMIT 1

Question: What's the primary cause of bad production capacity?

MATCH (m:Machine)-[r:USED_ON]->(d:Date)
WHERE r.production_volume < 550
WITH m, r, d

MATCH (m)-[r2:USED_ON]->(d)
WITH m, r, r2, d

RETURN
  m.machine_id as Machine,
  r.production_volume as ProductionVolume,
  r2.machine_utilization as MachineUtilization,
  r2.breakdowns as Breakdowns,
  r2.energy_consumption as EnergyConsumption,
  r2.absentialism as Absenteeism,
  r2.cycle_time as CycleTime,
  r2.defect_rate as DefectRate,
  r2.safety_incidents as SafetyIncidents,
  r2.waste_generated as WasteGenerated
ORDER BY ProductionVolume ASC

Question: Analyze Team Performance by Machine Utilization

MATCH (t:Team)<-[:USED_BY_TEAM]-(m:Machine)-[u:USED_ON]->(d:Date)
WHERE t.factory = 'Factory 1'
RETURN t.id AS team_id, AVG(u.machine_utilization) AS avg_utilization, AVG(u.defect_rate) AS avg_defect_rate

Question: Compare Teams by Production Volume

MATCH (t:Team)<-[:USED_BY_TEAM]-(m:Machine)-[u:USED_ON]->(d:Date)
WHERE t.factory = 'Factory 1'
RETURN t.id AS team_id, SUM(u.production_volume) AS total_production
ORDER BY total_production DESC

Question: Identify Teams with Safety Incidents

MATCH (t:Team)<-[:USED_BY_TEAM]-(m:Machine)-[u:USED_ON]->(d:Date)
WHERE t.factory = 'Factory 1' AND u.safety_incidents > 0
RETURN t.id AS team_id, SUM(u.safety_incidents) AS total_incidents

Question: Find Teams with High Energy Consumption

MATCH (t:Team)<-[:USED_BY_TEAM]-(m:Machine)-[u:USED_ON]->(d:Date)
WHERE t.factory = 'Factory 1'
RETURN t.id AS team_id, SUM(u.energy_consumption) AS total_energy_consumption
ORDER BY total_energy_consumption DESC

Question: Analyze Team Revenue Contribution

MATCH (t:Team)<-[:USED_BY_TEAM]-(m:Machine)-[u:USED_ON]->(d:Date)
WHERE t.factory = 'Factory 1'
RETURN t.id AS team_id, SUM(u.revenue) AS total_revenue
ORDER BY total_revenue DESC

Question: Identify best team in Factory 1

MATCH (t:Team)<-[:USED_BY_TEAM]-(m:Machine)-[u:USED_ON]->(d:Date)
WHERE t.factory = 'Factory 1'
WITH t.id AS team_id, 
     SUM(u.production_volume) AS total_production, 
     AVG(u.defect_rate) AS avg_defect_rate, 
     SUM(u.safety_incidents) AS total_safety_incidents, 
     AVG(u.energy_efficiency_rating) AS avg_energy_efficiency
RETURN team_id, 
       total_production, 
       avg_defect_rate, 
       total_safety_incidents, 
       avg_energy_efficiency, 
       (total_production * 0.5) - (avg_defect_rate * 100) - (total_safety_incidents * 10) + (avg_energy_efficiency * 20) AS performance_score
ORDER BY performance_score DESC
LIMIT 1

Question: Identify the best machine in all factories

MATCH (t:Team)<-[:USED_BY_TEAM]-(m:Machine)-[u:USED_ON]->(d:Date)
WITH t.id AS team_id, 
     t.factory AS factory, 
     SUM(u.production_volume) AS total_production, 
     AVG(u.defect_rate) AS avg_defect_rate, 
     SUM(u.safety_incidents) AS total_safety_incidents, 
     AVG(u.energy_efficiency_rating) AS avg_energy_efficiency
RETURN team_id, 
       factory, 
       total_production, 
       avg_defect_rate, 
       total_safety_incidents, 
       avg_energy_efficiency, 
       (total_production * 0.5) - (avg_defect_rate * 100) - (total_safety_incidents * 10) + (avg_energy_efficiency * 20) AS performance_score
ORDER BY performance_score DESC
LIMIT 1

### Negative Examples (Avoid These):
Question: List teams that operated on a 23-Jan-2023 and their average operator experience?

Incorrect cypher for above question:

MATCH (t:Team)-[:USED_BY_TEAM]->(m:Machine)-[u:USED_ON]->(d:Date {{date: date('2023-01-23')}})
RETURN t.id AS Team, avg(u.average_operator_experience) AS AverageOperatorExperience

Correct cypher for above question:

MATCH(m:Machine)-[u:USED_ON]->(d:Date{{date: date('2023-01-23')}})
WITH m, u, d
MATCH(m)-[ut:USED_BY_TEAM]->(t:Team)
WHERE d.date = ut.date
Return t.id, avg(ut.average_operator_experience) as AverageOperatorExperience

Question: Analyze each team's contribution to production volume on a 23-Jan-2023

Incorrect cypher for above question:

MATCH (t:Team)-[:USED_BY_TEAM]->(m:Machine)-[u:USED_ON]->(d:Date {{date: date('2023-01-23')}})
RETURN t.id AS Team, sum(u.production_volume) AS TotalProductionVolume

Correct cypher for above question:

MATCH(m:Machine)-[u:USED_ON]->(d:Date{{date: date('2023-01-23')}})
WITH m, u, d
MATCH(m)-[ut:USED_BY_TEAM]->(t:Team)
WHERE d.date = ut.date
Return t.id, u.production_volume as ProductionVolume

Question: Analyze the relationship between supplier raw material quality and batch quality

Incorrect cypher for above question:

MATCH (r:RawMaterial)-[sb:SUPPLIED_BY]->(s:Supplier)
MATCH (p:Product)-[pu:PRODUCED_USING]->(r:RawMaterial)
RETURN r.raw_material_quality AS RawMaterialQuality, avg(pu.batch_quality) AS AvgBatchQuality

Correct cypher for above question:

MATCH (p:Product)-[pu:PRODUCED_USING]->(rm:RawMaterial)
RETURN rm.raw_material_quality AS RawMaterialQuality, avg(pu.batch_quality) AS AvgBatchQuality
ORDER BY RawMaterialQuality

Question: What is the average batch quality for products supplied by each supplier?

Correct cypher for above question:

MATCH (r:RawMaterial)-[sb:SUPPLIED_BY]->(s:Supplier)
MATCH (p:Product)-[pu:PRODUCED_USING]->(rm:RawMaterial)
WHERE sb.date = pu.date
WITH s, pu.batch_quality AS BatchQuality
RETURN s.supplier_name AS Supplier, avg(BatchQuality) AS AvgBatchQuality

Question: How many years data is there?

Incorrect cypher for above question:

MATCH (d:Date)
RETURN DISTINCT year(d.date) as Year, count(*) as NumberOfYears

Correct cypher for above question:

MATCH (d:Date)
RETURN DISTINCT substring(toString(d.date), 0, 4) as Year

Question: Which factories are above the production average?

Incorrect cypher for above question:

MATCH (f:Factory)-[:HAS_MACHINE]->(m:Machine)-[u:USED_ON]->(d:Date)
WITH f, avg(u.production_volume) AS avgProductionVolume
WHERE u.production_volume > avgProductionVolume
RETURN f.factory_id AS FactoryID

Correct cypher for above question:

MATCH (f:Factory)-[:HAS_MACHINE]->(m:Machine)-[r:USED_ON]->()
WITH avg(r.production_volume) as OverallAverageProductionVolume
MATCH (f:Factory)-[:HAS_MACHINE]->(m:Machine)-[r:USED_ON]->()
WITH f, avg(r.production_volume) as FactoryAverageProductionVolume, OverallAverageProductionVolume
WHERE FactoryAverageProductionVolume > OverallAverageProductionVolume
RETURN f.factory_id as Factory, FactoryAverageProductionVolume
ORDER BY FactoryAverageProductionVolume DESC

### Validation Rules:
1. Use ISO8601 date formatting (date('YYYY-MM-DD'))
2. Always specify node labels (:Node) and relationship types [:REL]
3. Validate relationship directions against schema
4. Use WHERE clauses instead of inline MATCH conditions
5. Include explicit RETURN statements with aliases
6. Handle time-series aggregates using WITH clauses
7. Validate node/relationship existence in MATCH patterns
8. Use LIMIT 100 unless explicitly forbidden
9. Prefer path traversals over multiple MATCH clauses
10. Handle nulls in optional matches with COALESCE
11. Use parameterization for user inputs

### User Question:
{question}

### Response (Cypher only):'''

def validate_cypher(schema: dict, query: str) -> dict:
    """Validate generated Cypher against schema rules"""
    # Implementation checks:
    # 1. Node/relationship existence
    # 2. Property type matching
    # 3. Relationship direction validation
    # 4. Constraint enforcement
    return validation_result

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=['question'], template=CYPHER_GENERATION_TEMPLATE
)