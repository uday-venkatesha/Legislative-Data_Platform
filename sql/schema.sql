CREATE TABLE IF NOT EXISTS bills (
  bill_id               VARCHAR(128) NOT NULL,   -- OCD id, e.g. ocd-bill/... : natural key
  state                 VARCHAR(64)  NOT NULL,
  session               VARCHAR(64),
  identifier            VARCHAR(64),             -- "HB 2001"
  title                 TEXT,
  classification        VARCHAR(64),             -- bill, resolution, ...
  subjects              TEXT,                    -- pipe-joined for now (normalized in Phase 2)
  primary_sponsor       VARCHAR(255),
  primary_sponsor_party VARCHAR(64),
  furthest_stage        VARCHAR(32),             -- high-water mark: introduced/in_committee/passed_chamber/enacted
  lifecycle_state       VARCHAR(32),             -- active/dead/enacted, from latest action language
  first_action_date     DATE,
  latest_action_date    DATE,
  latest_action_desc    TEXT,
  openstates_url        VARCHAR(512),
  source_name           VARCHAR(64),             -- lineage: which pipeline wrote this row
  ingested_at           DATETIME,                -- lineage: when we loaded it
  updated_at_source     DATETIME,                -- when the source last changed it
  PRIMARY KEY (bill_id),
  KEY idx_state_session (state, session),
  KEY idx_furthest_stage (furthest_stage),
  KEY idx_lifecycle_state (lifecycle_state),
  KEY idx_latest_action (latest_action_date)
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS raw_bills (
  source          VARCHAR(32)  NOT NULL,
  source_bill_id  VARCHAR(160) NOT NULL,
  state_code      CHAR(2),
  payload         JSON         NOT NULL,
  fetched_at      DATETIME     NOT NULL,
  PRIMARY KEY (source, source_bill_id)
) CHARACTER SET utf8mb4;