-- =====================================================================
-- modemap データベース 復元スクリプト（リバースエンジニアリング版）
--
-- 出典: gas-projects/project2/data.js:10-18 の SQL 全文、および
--       summarize() (data.js:85-93) のテーブル/カテゴリ対応から復元。
-- 単位: 各カテゴリ列は「分」整数値（constructAnalytics で /60 して時間表示。
--       getModemap() が parseInt するため整数必須）。
--
-- ⚠ 値はすべて仮置き（キャリブレーション前の基準値）。
--    観測された唯一のアンカー: 原稿 analysis シートの出力例「大学 sketch 1.3」
--    （= plot「大学」の sketch 残り計 1.3時間。ページ数不明のため単価は逆算不可）
--    実運用する際は docs/MODEMAP_RESTORATION.md のキャリブレーション手順で
--    実測値に置き換えること。
-- =====================================================================

CREATE DATABASE IF NOT EXISTS modemap CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE modemap;

-- モード名マスタ。JOIN の基点テーブル。
CREATE TABLE mode (
  id   INT UNSIGNED NOT NULL AUTO_INCREMENT,
  mode VARCHAR(64)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_mode_name (mode)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 下記5テーブルは summarize(data.js:85) の集約単位と完全に一致する:
--   sketch    -> obj["sketch"]
--   lineart   -> head + body + cloth
--   object    -> item + background
--   illustrate-> base + shadow + erotic + line
--   effect    -> effect + erotic_effect + onomatopeia + front + back + dialog + mood

CREATE TABLE sketch (
  mode_id INT UNSIGNED NOT NULL,
  sketch  INT NOT NULL DEFAULT 0,
  PRIMARY KEY (mode_id),
  FOREIGN KEY (mode_id) REFERENCES mode(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE lineart (
  mode_id INT UNSIGNED NOT NULL,
  head    INT NOT NULL DEFAULT 0,
  body    INT NOT NULL DEFAULT 0,
  cloth   INT NOT NULL DEFAULT 0,
  PRIMARY KEY (mode_id),
  FOREIGN KEY (mode_id) REFERENCES mode(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE object (
  mode_id    INT UNSIGNED NOT NULL,
  item       INT NOT NULL DEFAULT 0,
  background INT NOT NULL DEFAULT 0,
  PRIMARY KEY (mode_id),
  FOREIGN KEY (mode_id) REFERENCES mode(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE illustrate (
  mode_id INT UNSIGNED NOT NULL,
  base    INT NOT NULL DEFAULT 0,
  shadow  INT NOT NULL DEFAULT 0,
  erotic  INT NOT NULL DEFAULT 0,
  line    INT NOT NULL DEFAULT 0,
  PRIMARY KEY (mode_id),
  FOREIGN KEY (mode_id) REFERENCES mode(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE effect (
  mode_id      INT UNSIGNED NOT NULL,
  effect       INT NOT NULL DEFAULT 0,
  erotic_effect INT NOT NULL DEFAULT 0,
  onomatopeia  INT NOT NULL DEFAULT 0,
  front        INT NOT NULL DEFAULT 0,
  back         INT NOT NULL DEFAULT 0,
  dialog       INT NOT NULL DEFAULT 0,
  mood         INT NOT NULL DEFAULT 0,
  PRIMARY KEY (mode_id),
  FOREIGN KEY (mode_id) REFERENCES mode(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 行（モード名）の復元: xlsx 実データに実在する値
--   standard, battle      … 原稿 lineart シート C列（18/17ページで観測）★必須
--   erotic                … concept lineart シート
--   csp                   … concept color シート
--   coverpage, coverhalf  … 原稿 color シート
-- ※ character / main-character / model は parts シート由来だが、
--   project2 は lineart のみ処理するため modemap には不要（schedule-init
--   側のモード体系と混同注意）。
-- ---------------------------------------------------------------------

INSERT INTO mode (mode) VALUES
  ('standard'),
  ('battle'),
  ('erotic'),
  ('csp'),
  ('coverpage'),
  ('coverhalf');

-- ---------------------------------------------------------------------
-- 仮置き値（分）。standard を基準、battle は効果・背景系を加重した例。
-- キャリブレーション前は「相対比の雛形」として扱うこと。
-- (mode, sketch, head, body, cloth, item, background, base, shadow, erotic, line, effect, erotic_effect, onomatopeia, front, back, dialog, mood)
-- ---------------------------------------------------------------------

INSERT INTO sketch (mode_id, sketch)
SELECT id, v FROM mode JOIN (SELECT 60 AS v) t ON mode='standard';
INSERT INTO sketch (mode_id, sketch)
SELECT id, 70 FROM mode WHERE mode='battle';
INSERT INTO sketch (mode_id, sketch)
SELECT id, 50 FROM mode WHERE mode IN ('erotic','csp','coverpage','coverhalf');

INSERT INTO lineart (mode_id, head, body, cloth)
SELECT id, 40, 40, 30 FROM mode WHERE mode IN ('standard','erotic');
INSERT INTO lineart (mode_id, head, body, cloth)
SELECT id, 45, 45, 35 FROM mode WHERE mode='battle';
INSERT INTO lineart (mode_id, head, body, cloth)
SELECT id, 30, 30, 25 FROM mode WHERE mode IN ('csp','coverpage','coverhalf');

INSERT INTO object (mode_id, item, background)
SELECT id, 25, 40 FROM mode WHERE mode IN ('standard','erotic','csp','coverpage','coverhalf');
INSERT INTO object (mode_id, item, background)
SELECT id, 30, 55 FROM mode WHERE mode='battle';

INSERT INTO illustrate (mode_id, base, shadow, erotic, line)
SELECT id, 20, 15, 25, 15 FROM mode WHERE mode IN ('standard','erotic');
INSERT INTO illustrate (mode_id, base, shadow, erotic, line)
SELECT id, 25, 20, 30, 20 FROM mode WHERE mode='battle';
INSERT INTO illustrate (mode_id, base, shadow, erotic, line)
SELECT id, 15, 10, 15, 10 FROM mode WHERE mode IN ('csp','coverpage','coverhalf');

INSERT INTO effect (mode_id, effect, erotic_effect, onomatopeia, front, back, dialog, mood)
SELECT id, 15, 20, 10, 10, 10, 10, 10 FROM mode WHERE mode IN ('standard','erotic','csp','coverpage','coverhalf');
INSERT INTO effect (mode_id, effect, erotic_effect, onomatopeia, front, back, dialog, mood)
SELECT id, 20, 25, 15, 15, 15, 10, 12 FROM mode WHERE mode='battle';

-- project2 の getModemapArray() と同等のフラット取得:
--   SELECT mode, sketch,head, body, cloth, item, background, base, shadow, erotic,
--          line, effect, erotic_effect, onomatopeia, front, back, dialog, mood
--   FROM modemap.mode
--   RIGHT JOIN sketch    ON modemap.mode.id = modemap.sketch.mode_id
--   RIGHT JOIN lineart   ON modemap.mode.id = modemap.lineart.mode_id
--   RIGHT JOIN object    ON modemap.mode.id = modemap.object.mode_id
--   RIGHT JOIN illustrate ON modemap.mode.id = modemap.illustrate.mode_id
--   RIGHT JOIN effect    ON modemap.mode.id = modemap.effect.mode_id;
