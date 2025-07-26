# bots_scripts



## SQL COMMANDS:
Insertar los comandos:

```
INSERT INTO rest_anexodocumento (creado_en, archivo, usuario_id, fecha) VALUES (now(), 'anexos/testing.xlsx', 1, '2025-03-26 12:00:00+00');

UPDATE rest_anexodocumento SET creado_en = date_trunc('second', creado_en) WHERE id=1;

INSERT INTO rest_anexoanexo (key, login, location, documento_find_id) VALUES (0000, '0000@mpfn.gob.pe', 'server', 1);
```