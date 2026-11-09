# Матрица функций CHEATLAB Launcher для Android

Статусы разделяют внесённый код, успешную сборку и тестирование на устройстве. Функция не считается готовой только потому, что для неё появилась кнопка или Rust-код собрался.

| Функция | Текущий статус | Примечание |
|---|---|---|
| Основа интерфейса Millida | Перенесена в сборку | Используется исходный React/TypeScript UI |
| CHEATLAB device login | Реализован в коде, ожидает Android build/device test | Вход через cheatlab.fun, подтверждение ссылки, возврат в приложение |
| Вход по ключу CHEATLAB | Реализован в коде, ожидает Android build/device test | clab2 key + email OTP |
| Хранение CHEATLAB-сессии | Реализован в коде, ожидает Android build/device test | Токен хранится через Rust encrypted vault, не возвращается в React |
| Отдельный Microsoft/офлайн игровой аккаунт | Существующий экран сохранён | Не смешивается с аккаунтом сайта |
| Нижняя мобильная навигация | Реализована в коде, ожидает Android device test | Играть, сборки, каталог, серверы, друзья |
| Адаптация узких экранов | Частично реализована | Safe areas, нижняя панель, диалоги, сенсорные кнопки; нужен тест всех экранов |
| Собственный CHEATLAB brand/icon | Реализован в build adapter | Новый application ID иконка и название |
| Minecraft Vanilla на Android | Не готово | Нужна ARM64 JVM через JNI и Android graphics backend |
| Fabric / Quilt | Не проверено | Требуется запуск на Android |
| Forge / NeoForge | Не проверено | Требуется проверка отдельных версий |
| Моды / Modrinth / CurseForge | Не проверено | Нужна Android file access/SAF |
| ZIP / MRPACK / packwiz | Не проверено | Нужен Android Storage Access Framework |
| Миры / резервные копии | Не проверено | SAF, URI permissions и app-private storage |
| Ресурспаки / шейдеры | Не проверено | Зависит от Android renderer и GPU |
| Сенсорное управление в Minecraft | Не готово | Сначала нужен Android game runtime + input bridge |
| Серверы / Quick Play | Не проверено | Нужна проверка на устройстве |
| Друзья / чат / голос | Не проверено | Нужны Android audio lifecycle и разрешения |

## Критерий релиза

APK считается только сборкой оболочки, пока Vanilla Minecraft не будет реально запущен на ARM64 Android, не появится работающий сенсорный input bridge и не будут проверены хранилище файлов, игровые аккаунты и основные разделы интерфейса.
