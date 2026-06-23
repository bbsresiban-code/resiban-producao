-- Migracao: hora de cada fardo na producao + controle de inicio/fim de turno
-- Rodar no Supabase > SQL Editor ANTES de subir o codigo novo.
-- Seguro reexecutar (IF NOT EXISTS). Nao apaga nem altera dados existentes.

-- 1) Hora do lancamento de cada fardo (para producao por hora / eficiencia).
--    Formato texto "HH:MM" (mesmo padrao de paradas_lavacao e producao_extrusao).
ALTER TABLE producao_lavacao ADD COLUMN IF NOT EXISTS hora TEXT;

-- 2) Controle de inicio/fim de turno (1 linha por data+turno).
CREATE TABLE IF NOT EXISTS turno_lavacao (
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
ALTER TABLE turno_lavacao DISABLE ROW LEVEL SECURITY;
