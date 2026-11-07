# Настоящий перенос Millida Launcher на Android

## Источник кода

- Репозиторий: https://github.com/millida/launcher
- Изученная ветка: `main`
- Проверенный исходный коммит: `a9cec042ad1515a495a4f7c550e71f7423b65812` (2026-11-05)
- Технологии: React 19 / TypeScript + Rust + Tauri 2.
- Это должен быть порт исходника Millida. Amethyst/Pojav не заменяет интерфейс или ядро Millida.

## Что уже есть в upstream

- `#[cfg_attr(mobile, tauri::mobile_entry_point)]` в `src-tauri/src/lib.rs`.
- Android launcher icons в `src-tauri/icons/android/`.
- Общие React/TypeScript экраны и Rust-команды, которые можно использовать в мобильной сборке.

Это ещё не означает, что Android-сборка готова: в исходнике почти нет `target_os = "android"`-реализаций, а код запуска Minecraft использует обычный процесс Java.

## Блокеры, которые надо закрыть

1. **Сборка Tauri Android.** Сгенерировать Android-проект командой `tauri android init`, собрать Rust для `aarch64-linux-android`, разделить desktop-only plugins/команды и mobile-supported plugins. У Tauri есть официальный Android build workflow; он сам по себе не переносит desktop-only функции.
2. **Системные функции.** Desktop tray, global shortcuts, updater, single-instance и второе overlay-окно нужно исключить из Android target или заменить Android API. Основной экран должен оставаться тем же React UI.
3. **Файлы и разрешения.** Настольные file/folder dialogs и абсолютные пути нужно заменить Android Storage Access Framework (SAF) и app-private storage с корректными URI/grants.
4. **Minecraft Java runtime.** Сейчас `engine/game/launch.rs` создаёт внешний Java-процесс через `std::process::Command`, а `engine/game/java.rs` ищет desktop `bin/java`. Android требует ARM64 OpenJDK, вызов JVM через JNI/Android native layer, передачу classpath/JVM options, управление жизненным циклом Activity и нативные LWJGL/OpenGL библиотеки.
5. **Графика и управление.** Нужны Android surface, сенсорный контроллер, экранная клавиатура, мышь/геймпад и адаптированный ввод. Поддержка шейдеров зависит от выбранного GLES/Vulkan backend и GPU.
6. **Каталоги и загрузчики.** Сохранить общую логику загрузок, метаданных и проверки файлов из Millida. Отдельно проверять Vanilla/Fabric/Forge/NeoForge/Quilt на конкретных версиях и Android runtime.
7. **Аккаунты и сервисы.** Для публичного форка нельзя переносить закрытые ключи и официальные updater credentials. Microsoft/Discord OAuth требуют собственной регистрации; сервисы Millida доступны только в рамках правил их владельца.
8. **Адаптация экранов.** Пройти все основные экраны на телефоне: навигация, боковые панели, диалоги, профили, каталог, настройки, моды, миры, серверы, аккаунты, чат/социальные разделы. Не считать web-build доказательством мобильной пригодности.

## Порядок работ

- [ ] Подключить upstream `millida/launcher` как единственный источник интерфейса и ядра.
- [ ] Сгенерировать Android project через официальный Tauri CLI.
- [ ] Добавить desktop/mobile cfg для plugin setup, tray, updater, global shortcuts и вторичных окон.
- [ ] Собрать первый APK с настоящим Millida React UI и диагностировать все Rust/Gradle ошибки.
- [ ] Подключить Android file picker/SAF.
- [ ] Интегрировать ARM64 Java runtime через JNI и графический backend (не запуск Amethyst UI).
- [ ] Реально запустить Vanilla и проверить логи/закрытие/повторный старт.
- [ ] По очереди проверить Fabric, Forge, NeoForge, Quilt.
- [ ] Перенести и проверить моды, ZIP/MRPACK, ресурспаки, шейдеры, миры, серверы и остальные экраны.
- [ ] Собрать подписанный APK с постоянным release keystore, который хранится только в GitHub Secrets.
- [ ] Выпустить релиз только после smoke-test на Android устройстве.

## Лицензия и товарный знак

- Исходный код Millida Launcher: GPL-3.0-only. Сохранять `LICENSE`, уведомления и исходный код изменений при распространении.
- Upstream `TRADEMARK.ru.md` прямо требует от публичных форков отличимого имени, package ID и визуального бренда. Допустимо фактически написать «неофициальный форк, основанный на Millida Launcher», но нельзя представлять APK как официальный продукт Millida.
- Не использовать официальный ключ подписи, Microsoft client ID, Discord app ID и приватные updater keys.
- Не обещать работу официальных Millida API из неофициального клиента.

## Критерий релиза

APK не публикуется как «готовый порт» только потому, что APK собрался. Критерии: исходный Millida UI отображается, native Rust IPC работает, данные сохраняются, Vanilla Java реально запускается на ARM64 Android, загрузчики и содержимое проверены, сенсорное управление работает, а ограничения неизвестных модов/шейдеров честно описаны.
