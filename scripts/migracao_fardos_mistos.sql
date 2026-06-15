-- Migracao: permitir fardoes E fardinhos na mesma NF de aparas (carga mista)
-- Rodar no Supabase > SQL Editor ANTES de subir o codigo novo.
-- Seguro reexecutar (IF NOT EXISTS). Nao apaga nem altera dados existentes.
--
-- Modelo: peso_kg e quantidade continuam TOTAIS da NF.
--         qtd_fardao + qtd_fardinho detalham a composicao.
--         Linhas antigas ficam com 0/0 e o app deriva do tipo_fardo+quantidade.

ALTER TABLE aparas_estoque  ADD COLUMN IF NOT EXISTS qtd_fardao    INTEGER DEFAULT 0;
ALTER TABLE aparas_estoque  ADD COLUMN IF NOT EXISTS qtd_fardinho  INTEGER DEFAULT 0;

ALTER TABLE op_lavacao_nfs  ADD COLUMN IF NOT EXISTS qtd_fardao    INTEGER DEFAULT 0;
ALTER TABLE op_lavacao_nfs  ADD COLUMN IF NOT EXISTS qtd_fardinho  INTEGER DEFAULT 0;

ALTER TABLE producao_lavacao ADD COLUMN IF NOT EXISTS qtd_fardao   INTEGER DEFAULT 0;
ALTER TABLE producao_lavacao ADD COLUMN IF NOT EXISTS qtd_fardinho INTEGER DEFAULT 0;

-- (Opcional) Preencher o breakdown das linhas JA existentes a partir do tipo_fardo.
-- Nao e obrigatorio: o app ja deriva sozinho. Rode se quiser os valores gravados.

UPDATE aparas_estoque
   SET qtd_fardao = COALESCE(quantidade, 0)
 WHERE LOWER(COALESCE(tipo_fardo, '')) = 'fardao'
   AND COALESCE(qtd_fardao, 0) = 0 AND COALESCE(qtd_fardinho, 0) = 0;
UPDATE aparas_estoque
   SET qtd_fardinho = COALESCE(quantidade, 0)
 WHERE LOWER(COALESCE(tipo_fardo, '')) = 'fardinho'
   AND COALESCE(qtd_fardao, 0) = 0 AND COALESCE(qtd_fardinho, 0) = 0;

UPDATE op_lavacao_nfs
   SET qtd_fardao = COALESCE(quant_fardos, 0)
 WHERE LOWER(COALESCE(tipo_fardo, '')) = 'fardao'
   AND COALESCE(qtd_fardao, 0) = 0 AND COALESCE(qtd_fardinho, 0) = 0;
UPDATE op_lavacao_nfs
   SET qtd_fardinho = COALESCE(quant_fardos, 0)
 WHERE LOWER(COALESCE(tipo_fardo, '')) = 'fardinho'
   AND COALESCE(qtd_fardao, 0) = 0 AND COALESCE(qtd_fardinho, 0) = 0;

UPDATE producao_lavacao
   SET qtd_fardao = COALESCE(quantidade, 0)
 WHERE LOWER(COALESCE(tipo_fardo, '')) = 'fardao'
   AND COALESCE(qtd_fardao, 0) = 0 AND COALESCE(qtd_fardinho, 0) = 0;
UPDATE producao_lavacao
   SET qtd_fardinho = COALESCE(quantidade, 0)
 WHERE LOWER(COALESCE(tipo_fardo, '')) = 'fardinho'
   AND COALESCE(qtd_fardao, 0) = 0 AND COALESCE(qtd_fardinho, 0) = 0;
