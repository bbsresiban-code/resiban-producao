-- Migracao: hora real da analise de laboratorio.
-- Rodar no Supabase > SQL Editor ANTES de subir o codigo novo.
-- Seguro reexecutar (IF NOT EXISTS). Nao apaga nem altera dados existentes.
-- A tabela qualidade ja existe e ja esta com RLS desabilitado.

ALTER TABLE qualidade ADD COLUMN IF NOT EXISTS hora TEXT;  -- "HH:MM" da analise
