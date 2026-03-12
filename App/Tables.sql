DROP DATABASE IF EXISTS nhs_database;
CREATE DATABASE nhs_database;
USE nhs_database;

-- =========================
-- TABLES
-- =========================

CREATE TABLE Country (
    CountryID   INT PRIMARY KEY,
    CountryName VARCHAR(80) NOT NULL
);

CREATE TABLE County (
    CountyID    INT PRIMARY KEY,
    CountyName  VARCHAR(80) NOT NULL,
    CountryID   INT NOT NULL,
    CONSTRAINT fk_county_country
        FOREIGN KEY (CountryID)
        REFERENCES Country(CountryID)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE District (
    DistrictID   INT PRIMARY KEY,
    DistrictName VARCHAR(80) NOT NULL,
    CountyID     INT NOT NULL,
    CONSTRAINT fk_district_county
        FOREIGN KEY (CountyID)
        REFERENCES County(CountyID)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE HealthcareOrganisation (
    OrgID       INT PRIMARY KEY,
    OrgName     VARCHAR(120) NOT NULL,
    OrgType     VARCHAR(40)  NOT NULL,
    AddressLine VARCHAR(150),
    City        VARCHAR(60),
    Postcode    VARCHAR(15),
    DistrictID  INT NOT NULL,
    CONSTRAINT fk_org_district
        FOREIGN KEY (DistrictID)
        REFERENCES District(DistrictID)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE Hospital (
    OrgID        INT PRIMARY KEY,
    BedCapacity  INT,
    HasEmergency BOOLEAN,
    CONSTRAINT fk_hospital_org
        FOREIGN KEY (OrgID)
        REFERENCES HealthcareOrganisation(OrgID)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE GPPractice (
    OrgID        INT PRIMARY KEY,
    NumGPs       INT,
    OpeningHours VARCHAR(80),
    CONSTRAINT fk_gp_org
        FOREIGN KEY (OrgID)
        REFERENCES HealthcareOrganisation(OrgID)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE SocioeconomicGroup (
    SEGCode     VARCHAR(20) PRIMARY KEY,
    SEGName     VARCHAR(80) NOT NULL,
    Description VARCHAR(200)
);

CREATE TABLE Patient (
    PatientID   INT PRIMARY KEY,
    NHSNumber   VARCHAR(20) UNIQUE,
    FirstName   VARCHAR(60),
    LastName    VARCHAR(60),
    DOB         DATE,
    Gender      CHAR(1),
    Street      VARCHAR(150),
    City        VARCHAR(60),
    Postcode    VARCHAR(15),
    DistrictID  INT NOT NULL,
    SEGCode     VARCHAR(20) NOT NULL,
    CONSTRAINT fk_patient_district
        FOREIGN KEY (DistrictID)
        REFERENCES District(DistrictID)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_patient_seg
        FOREIGN KEY (SEGCode)
        REFERENCES SocioeconomicGroup(SEGCode)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE PatientPhone (
    PatientID INT NOT NULL,
    Phone     VARCHAR(25) NOT NULL,
    PRIMARY KEY (PatientID, Phone),
    CONSTRAINT fk_phone_patient
        FOREIGN KEY (PatientID)
        REFERENCES Patient(PatientID)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE ProcedureType (
    ProcedureCode  VARCHAR(20) PRIMARY KEY,
    ProcedureName  VARCHAR(120) NOT NULL,
    Category       VARCHAR(60)
);

CREATE TABLE Encounter (
    EncounterID       INT PRIMARY KEY,
    PatientID         INT NOT NULL,
    OrgID             INT NOT NULL,
    EncounterDateTime DATETIME NOT NULL,
    EncounterType     VARCHAR(40),
    DistrictID        INT,
    ProcedureCode     VARCHAR(20),
    CONSTRAINT fk_enc_patient
        FOREIGN KEY (PatientID) REFERENCES Patient(PatientID),
    CONSTRAINT fk_enc_org
        FOREIGN KEY (OrgID) REFERENCES HealthcareOrganisation(OrgID),
    CONSTRAINT fk_enc_district
        FOREIGN KEY (DistrictID) REFERENCES District(DistrictID),
    CONSTRAINT fk_enc_procedure
        FOREIGN KEY (ProcedureCode) REFERENCES ProcedureType(ProcedureCode)
);

CREATE TABLE WaitingListEntry (
    WaitingID         INT PRIMARY KEY,
    PatientID         INT NOT NULL,
    OrgID             INT NOT NULL,
    ProcedureCode     VARCHAR(20) NOT NULL,
    RequestDate       DATE NOT NULL,
    Status            VARCHAR(20) NOT NULL,
    Priority          INT,
    EstimatedWaitDays INT,
    CONSTRAINT fk_wait_patient
        FOREIGN KEY (PatientID)
        REFERENCES Patient(PatientID)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_wait_org
        FOREIGN KEY (OrgID)
        REFERENCES HealthcareOrganisation(OrgID)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_wait_proc
        FOREIGN KEY (ProcedureCode)
        REFERENCES ProcedureType(ProcedureCode)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE PopulationFact (
    PopID           INT PRIMARY KEY,
    DistrictID      INT NOT NULL,
    RefDate         DATE NOT NULL,
    AgeGroup        VARCHAR(20) NOT NULL,
    SEGCode         VARCHAR(20) NOT NULL,
    PopulationCount INT NOT NULL,
    CONSTRAINT fk_pop_district
        FOREIGN KEY (DistrictID) REFERENCES District(DistrictID),
    CONSTRAINT fk_pop_seg
        FOREIGN KEY (SEGCode) REFERENCES SocioeconomicGroup(SEGCode)
);

CREATE TABLE FirstMinister (
    MinisterID   INT PRIMARY KEY,
    CountryID    INT NOT NULL,
    MinisterName VARCHAR(80) NOT NULL,
    TermStart    DATE,
    TermEnd      DATE,
    CONSTRAINT fk_min_country
        FOREIGN KEY (CountryID) REFERENCES Country(CountryID)
);

CREATE TABLE PolicyStatement (
    StatementID   INT PRIMARY KEY,
    MinisterID    INT NOT NULL,
    StatementDate DATE NOT NULL,
    Topic         VARCHAR(80),
    Content       TEXT,
    CONSTRAINT fk_statement_min
        FOREIGN KEY (MinisterID) REFERENCES FirstMinister(MinisterID)
);
