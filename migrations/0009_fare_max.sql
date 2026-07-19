-- distance-tiered corridors (intermunicipal): full-trip fare in addition to the
-- base fare_mxn, shown as "desde $8 hasta $17 según destino" (e.g. Tehuacán–Ajalpan
-- was $17 full / $8 intermediate stops per 2020 reporting).
ALTER TABLE combi_lines ADD COLUMN fare_max_mxn REAL;
