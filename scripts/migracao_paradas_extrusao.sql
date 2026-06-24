-- Migracao: registro de paradas da Extrusao (mesmo modelo de paradas_lavacao)
-- Rodar no Supabase > SQL Editor ANTES de subir o codigo novo.
-- Seguro reexecutar (IF NOT EXISTS). Nao apaga nem altera dados existentes.
-- Substitui a antiga aba "Manutencao" da Extrusao por "Paradas" (tipo_parada:
-- Manutencao Corretiva | Corretiva Programada | Manutencao Preventiva).

CREATE TABLE IF NOT EXISTS paradas_extrusao (
    id TEXT PRIMARY KEY,
    data DATE,
    turno TEXT,                 -- A | B | C
    tipo_parada TEXT,           -- Manutencao Corretiva | Corretiva Programada | Manutencao Preventiva
    hora_inicio TEXT,           -- "HH:MM"
    hora_fim TEXT,              -- "HH:MM"
    duracao_min INTEGER,
    observacao TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE paradas_extrusao DISABLE ROW LEVEL SECURITY;
