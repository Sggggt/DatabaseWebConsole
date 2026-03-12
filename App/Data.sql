USE nhs_database;

-- Country
INSERT INTO Country (CountryID, CountryName) VALUES
(1, 'England'),
(2, 'Scotland'),
(3, 'Wales'),
(4, 'Northern Ireland'),
(5, 'Region A'),
(6, 'Region B'),
(7, 'Region C'),
(8, 'Region D'),
(9, 'Region E'),
(10, 'Region F');

-- County
INSERT INTO County (CountyID, CountyName, CountryID) VALUES
(101, 'Greater London', 1),
(102, 'Essex', 1),
(103, 'Cambridgeshire', 1),
(104, 'Greater Manchester', 1),
(105, 'Merseyside', 1),
(106, 'West Midlands', 1),
(107, 'Glasgow City', 2),
(108, 'Edinburgh City', 2),
(109, 'Cardiff', 3),
(110, 'Belfast', 4);

-- District
INSERT INTO District (DistrictID, DistrictName, CountyID) VALUES
(1001, 'City of London', 101),
(1002, 'Tower Hamlets', 101),
(1003, 'Chelmsford', 102),
(1004, 'Colchester', 102),
(1005, 'Cambridge', 103),
(1006, 'Manchester', 104),
(1007, 'Liverpool', 105),
(1008, 'Birmingham', 106),
(1009, 'Glasgow Central', 107),
(1010, 'Cardiff Central', 109);

-- Socioeconomic groups
INSERT INTO SocioeconomicGroup (SEGCode, SEGName, Description) VALUES
('CHILD', 'Child', 'Age < 16'),
('ADULT', 'Adult', '16-64'),
('PENSION', 'Pensioner', '65+'),
('EMP', 'Employed', 'Employed full-time'),
('SEMP', 'Self-employed', 'Business / contractor'),
('UNEMP', 'Unemployed', 'Looking for job'),
('STUD', 'Student', 'Full-time student'),
('PRO', 'Professional', 'High-income professions'),
('LOWINC', 'Low income', 'Below threshold'),
('OTHER', 'Other', 'Not classified');

-- Healthcare organisations
INSERT INTO HealthcareOrganisation
    (OrgID, OrgName, OrgType, AddressLine, City, Postcode, DistrictID)
VALUES
(2001, 'St Thomas Hospital', 'HOSPITAL', '1 Westminster Bridge Rd', 'London', 'SE1 7EH', 1001),
(2002, 'Royal London Hospital', 'HOSPITAL', 'Whitechapel Rd', 'London', 'E1 1FR', 1002),
(2003, 'Chelmsford Community Hospital', 'HOSPITAL', '124 Broomfield Rd', 'Chelmsford', 'CM1 1AA', 1003),
(2004, 'Colchester General Hospital', 'HOSPITAL', 'Turner Rd', 'Colchester', 'CO4 5JL', 1004),
(2005, 'Cambridge GP Group', 'GP', '45 Hills Rd', 'Cambridge', 'CB2 1NT', 1005),
(2006, 'Manchester Ortho Centre', 'CONSULTANT', '17 Oxford Rd', 'Manchester', 'M1 6EY', 1006),
(2007, 'Liverpool GP Practice', 'GP', '22 Dock St', 'Liverpool', 'L1 4AB', 1007),
(2008, 'Birmingham Heart Hospital', 'HOSPITAL', '90 Main St', 'Birmingham', 'B1 2AA', 1008),
(2009, 'Glasgow Royal Infirmary', 'HOSPITAL', '84 Castle St', 'Glasgow', 'G4 0SF', 1009),
(2010, 'Cardiff Bay Clinic', 'CONSULTANT', '12 Bay Rd', 'Cardiff', 'CF10 5AB', 1010),
(2011, 'Essex Heart Centre', 'HOSPITAL', '2 River Walk', 'Chelmsford', 'CM1 2BB', 1003),
(2012, 'Manchester City Hospital', 'HOSPITAL', '50 Deansgate', 'Manchester', 'M3 2GH', 1006),
(2013, 'Liverpool Central Hospital', 'HOSPITAL', '88 Lime St', 'Liverpool', 'L1 1AB', 1007),
(2014, 'Cambridge Royal Hospital', 'HOSPITAL', '72 Kings Parade', 'Cambridge', 'CB2 1RQ', 1005),
(2015, 'City of London GP', 'GP', '3 Bishopsgate', 'London', 'EC2M 3AB', 1001),
(2016, 'Tower Health GP', 'GP', '18 Stepney Way', 'London', 'E1 2JL', 1002),
(2017, 'Chelmsford Riverside GP', 'GP', '12 River St', 'Chelmsford', 'CM1 4DD', 1003),
(2018, 'Colchester Family GP', 'GP', '21 North Rd', 'Colchester', 'CO4 7GH', 1004),
(2019, 'Cambridge Lakes GP', 'GP', '6 Mill Rd', 'Cambridge', 'CB1 2AD', 1005),
(2020, 'Manchester Central GP', 'GP', '5 Piccadilly', 'Manchester', 'M1 1AF', 1006),
(2021, 'Liverpool Bay GP', 'GP', '14 Dockside', 'Liverpool', 'L2 8AA', 1007),
(2022, 'Cardiff West GP', 'GP', '9 West St', 'Cardiff', 'CF11 6AA', 1010);

-- Hospital details (for hospital-type orgs)
INSERT INTO Hospital (OrgID, BedCapacity, HasEmergency) VALUES
(2001, 800, TRUE),
(2002, 700, TRUE),
(2003, 200, FALSE),
(2004, 300, TRUE),
(2008, 550, TRUE),
(2009, 650, TRUE),
(2011, 320, TRUE),
(2012, 480, TRUE),
(2013, 410, TRUE),
(2014, 360, FALSE);

-- GP practice details
INSERT INTO GPPractice (OrgID, NumGPs, OpeningHours) VALUES
(2005, 25, '08:00-18:00'),
(2007, 18, '08:30-17:30'),
(2015, 15, '08:00-18:00'),
(2016, 12, '08:30-17:30'),
(2017, 10, '08:00-17:00'),
(2018, 11, '08:30-17:30'),
(2019, 13, '08:00-18:30'),
(2020, 16, '08:00-18:00'),
(2021, 9,  '08:30-17:00'),
(2022, 14, '08:00-18:00');

-- Patients
INSERT INTO Patient
    (PatientID, NHSNumber, FirstName, LastName, DOB, Gender, Street, City, Postcode, DistrictID, SEGCode)
VALUES
(3001, 'NHS000001', 'Alice', 'Green', '1985-03-12', 'F', '10 King St', 'London', 'SE1 2AB', 1001, 'EMP'),
(3002, 'NHS000002', 'Bob', 'Smith', '1978-11-02', 'M', '5 Queen St', 'London', 'E1 3CD', 1002, 'UNEMP'),
(3003, 'NHS000003', 'Carol', 'Jones', '1990-06-21', 'F', '22 New Rd', 'Chelmsford', 'CM1 9XX', 1003, 'EMP'),
(3004, 'NHS000004', 'David', 'Brown', '1965-01-30', 'M', '7 Hill View', 'Colchester', 'CO4 6YY', 1004, 'PENSION'),
(3005, 'NHS000005', 'Eve', 'Miller', '2005-12-09', 'F', '3 Trinity St', 'Cambridge', 'CB2 1AA', 1005, 'STUD'),
(3006, 'NHS000006', 'Frank', 'Wilson', '1955-07-18', 'M', '1 Dean St', 'Manchester', 'M1 3BB', 1006, 'PENSION'),
(3007, 'NHS000007', 'Grace', 'Taylor', '1988-09-15', 'F', '99 Albert Dock', 'Liverpool', 'L1 8CD', 1007, 'EMP'),
(3008, 'NHS000008', 'Henry', 'Walker', '1972-04-04', 'M', '8 Canal St', 'Birmingham', 'B1 1CC', 1008, 'SEMP'),
(3009, 'NHS000009', 'Ivy', 'Hall', '1999-10-10', 'F', '4 River Rd', 'Glasgow', 'G4 1DD', 1009, 'EMP'),
(3010, 'NHS000010', 'Jack', 'Young', '1982-02-28', 'M', '6 Bay St', 'Cardiff', 'CF10 9ZZ', 1010, 'EMP');

-- Patient phone numbers
INSERT INTO PatientPhone (PatientID, Phone) VALUES
(3001, '+44-7000-111001'),
(3002, '+44-7000-111002'),
(3003, '+44-7000-111003'),
(3004, '+44-7000-111004'),
(3005, '+44-7000-111005'),
(3006, '+44-7000-111006'),
(3007, '+44-7000-111007'),
(3008, '+44-7000-111008'),
(3009, '+44-7000-111009'),
(3010, '+44-7000-111010');

-- Procedure types
INSERT INTO ProcedureType (ProcedureCode, ProcedureName, Category) VALUES
('HIP', 'Hip Replacement', 'Orthopaedics'),
('KNEE', 'Knee Replacement', 'Orthopaedics'),
('CATA', 'Cataract Surgery', 'Ophthalmology'),
('CARD', 'Cardiology Check', 'Cardiology'),
('DERM', 'Dermatology Consult', 'Dermatology'),
('ENT', 'ENT Consult', 'ENT'),
('MRI', 'MRI Scan', 'Imaging'),
('XRAY', 'X-Ray', 'Imaging'),
('PHYS', 'Physiotherapy Session', 'Rehab'),
('DENT', 'Dental Treatment', 'Dental');

-- Encounters
INSERT INTO Encounter
    (EncounterID, PatientID, OrgID, EncounterDateTime, EncounterType, DistrictID, ProcedureCode)
VALUES
(4001, 3001, 2001, '2025-10-20 09:15:00', 'ADMISSION', 1001, 'CARD'),
(4002, 3002, 2002, '2025-10-20 10:00:00', 'VISIT', 1002, 'ENT'),
(4003, 3003, 2003, '2025-10-21 11:30:00', 'VISIT', 1003, NULL),
(4004, 3004, 2004, '2025-10-21 14:00:00', 'ADMISSION', 1004, 'HIP'),
(4005, 3005, 2005, '2025-10-22 09:00:00', 'VISIT', 1005, NULL),
(4006, 3006, 2006, '2025-10-22 10:45:00', 'CONSULT', 1006, 'HIP'),
(4007, 3007, 2007, '2025-10-23 13:15:00', 'VISIT', 1007, 'DERM'),
(4008, 3008, 2008, '2025-10-23 15:30:00', 'ADMISSION', 1008, 'CARD'),
(4009, 3009, 2009, '2025-10-24 08:50:00', 'VISIT', 1009, 'PHYS'),
(4010, 3010, 2010, '2025-10-24 09:20:00', 'CONSULT', 1010, 'CATA');

-- Waiting list entries
INSERT INTO WaitingListEntry
    (WaitingID, PatientID, OrgID, ProcedureCode, RequestDate, Status, Priority, EstimatedWaitDays)
VALUES
(5001, 3001, 2001, 'HIP',  '2025-10-01', 'WAITING', 1, 90),
(5002, 3002, 2002, 'HIP',  '2025-10-02', 'WAITING', 2, 120),
(5003, 3003, 2003, 'CATA', '2025-10-03', 'WAITING', 3, 30),
(5004, 3004, 2004, 'KNEE', '2025-10-04', 'SCHEDULED', 2, 15),
(5005, 3005, 2005, 'ENT',  '2025-10-05', 'WAITING', 4, 10),
(5006, 3006, 2006, 'HIP',  '2025-10-06', 'WAITING', 1, 80),
(5007, 3007, 2007, 'DERM', '2025-10-07', 'WAITING', 5, 20),
(5008, 3008, 2008, 'CARD', '2025-10-08', 'WAITING', 2, 40),
(5009, 3009, 2009, 'PHYS', '2025-10-09', 'WAITING', 3, 14),
(5010, 3010, 2010, 'HIP',  '2025-10-10', 'WAITING', 2, 95);

-- Population facts
INSERT INTO PopulationFact
    (PopID, DistrictID, RefDate, AgeGroup, SEGCode, PopulationCount)
VALUES
(6001, 1001, '2025-10-20', 'ADULT', 'EMP', 50000),
(6002, 1002, '2025-10-20', 'ADULT', 'UNEMP', 20000),
(6003, 1003, '2025-10-20', 'ADULT', 'EMP', 15000),
(6004, 1004, '2025-10-20', 'ADULT', 'EMP', 12000),
(6005, 1005, '2025-10-20', 'ADULT', 'STUD', 9000),
(6006, 1006, '2025-10-20', 'ADULT', 'EMP', 30000),
(6007, 1007, '2025-10-20', 'ADULT', 'EMP', 18000),
(6008, 1008, '2025-10-20', 'ADULT', 'SEMP', 16000),
(6009, 1009, '2025-10-20', 'ADULT', 'EMP', 14000),
(6010, 1010, '2025-10-20', 'ADULT', 'EMP', 11000);

-- First ministers
INSERT INTO FirstMinister (MinisterID, CountryID, MinisterName, TermStart, TermEnd) VALUES
(7001, 1, 'Alex Carter', '2023-05-01', NULL),
(7002, 2, 'Fiona McKay', '2022-07-15', NULL),
(7003, 3, 'Gareth Davies', '2024-01-10', NULL),
(7004, 4, 'Siobhan O\'Neill', '2023-03-20', NULL),
(7005, 5, 'Jordan Lee', '2024-06-01', NULL),
(7006, 6, 'Taylor Brooks', '2024-02-01', NULL),
(7007, 7, 'Morgan Patel', '2024-04-12', NULL),
(7008, 8, 'Casey Nguyen', '2024-08-05', NULL),
(7009, 9, 'Riley Chen', '2024-09-09', NULL),
(7010, 10, 'Jamie Walker', '2024-11-01', NULL);

-- Policy statements
INSERT INTO PolicyStatement (StatementID, MinisterID, StatementDate, Topic, Content) VALUES
(8001, 7001, '2025-01-15', 'Elective Recovery', 'Increasing theatre capacity for hip and knee replacements.'),
(8002, 7002, '2025-01-18', 'Digital Health', 'Expanding virtual clinics across urban hospitals.'),
(8003, 7003, '2025-01-20', 'Primary Care', 'Recruiting additional GPs for Cardiff region.'),
(8004, 7004, '2025-01-22', 'Emergency Care', 'Upgrading A&E units with new triage protocols.'),
(8005, 7005, '2025-01-25', 'Cancer Pathways', 'Reducing diagnostic wait times with new equipment.'),
(8006, 7006, '2025-01-27', 'Mental Health', 'Adding community support teams for early intervention.'),
(8007, 7007, '2025-01-29', 'Workforce', 'Scholarships for nursing and allied health students.'),
(8008, 7008, '2025-02-02', 'Public Health', 'Vaccination outreach in underserved districts.'),
(8009, 7009, '2025-02-05', 'Data & Analytics', 'Standardizing data feeds for national dashboards.'),
(8010, 7010, '2025-02-07', 'Cardiology', 'Funding cath labs to cut cardiac wait lists.');
