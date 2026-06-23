-- Migracao: controle de turno na extrusao + material extra na OPE (master)
-- Rodar no Supabase > SQL Editor ANTES de subir o codigo novo.
-- Seguro reexecutar (IF NOT EXISTS). Nao apaga nem altera dados existentes.
-- IMPORTANTE: tabela nova nasce com RLS ligado neste projeto -> incluir o DISABLE.

-- 1) Inicio/fim de turno da extrusao (1 linha por data+turno).
CREATE TABLE IF NOT EXISTS turno_extrusao (
    id TEXT PRIMARY KEY,
    data DATE,
    turno TEXT,                 -- A | B | C
    numero_op TEXT,
    hora_inicio TEXT,           -- "HH:MM"
    hora_fim TEXT,              -- "HH:MM"
    registrado_por TEXT,
    observacao TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE turno_extrusao DISABLE ROW LEVEL SECURITY;

-- 2) Material extra lancado pelo master numa OPE (sem origem em OPL/NF).
--    Soma ao volume previsto da OPE e aparece na rastreabilidade.
CREATE TABLE IF NOT EXISTS ope_material_extra (
    id TEXT PRIMARY KEY,
    numero_op TEXT,             -- OPE-XXXX
    descricao TEXT,             -- o que e o material
    tipo_justificativa TEXT,    -- Limpo | Repasse | Sem NF
    peso_kg NUMERIC,
    registrado_por TEXT,
    observacao TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE ope_material_extra DISABLE ROW LEVEL SECURITY;
