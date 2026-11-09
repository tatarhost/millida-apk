# Перенос Millida UI/core в CHEATLAB Launcher на Android

## Источник

- Upstream: https://github.com/millida/launcher
- Зафиксированный исходный коммит: `a9cec042ad1515a495a4f7c550e71f7423b65812`
- Стек: React 19 / TypeScript + Rust + Tauri 2.
- Продукт форка: **CHEATLAB Launcher**, сайт: https://cheatlab.fun.
- Это не официальный продукт Millida. Брендинг upstream не копируется.

## Уже внесено в Android adapter

- собран Android-вариант настоящего upstream интерфейса и Rust core;
- собственное имя, application ID, логотип и Android mipmap icons;
- нижняя панель навигации, touch-friendly controls и safe-area layout;
- скрытие desktop titlebar и desktop sidebar на телефоне;
- отдельный CHEATLAB device authorization flow;
- страница browser approval на cheatlab.fun; после входа/регистрации подтверждение возвращает пользователя в Android app;
- вход по `clab2-…` ключу CHEATLAB с email OTP;
- native Rust bridge сохраняет CHEATLAB bearer token в зашифрованном vault и не возвращает его в React;
- вход в CHEATLAB отделён от игрового Microsoft/offline аккаунта.

## Схема входа CHEATLAB

1. Android app создаёт device code и получает ссылку `https://cheatlab.fun/app-authorize.html`.
2. Пользователь входит или регистрируется в своём аккаунте на сайте.
3. Страница подтверждает device code через Worker endpoint `/api/app-auth/approve`.
4. Приложение опрашивает `/api/app-auth/poll`; Worker выдаёт отдельную сессию, привязанную к client ID Android-установки.
5. Нативная команда Rust сохраняет токен в encrypted vault; UI получает только публичные сведения аккаунта.
6. После этого пользователь отдельно подключает Microsoft или офлайн игровой аккаунт.

Device code живёт около пяти минут и может быть использован один раз. Альтернативный вход по login key использует существующие CHEATLAB API `/api/auth/keylogin` и `/api/auth/login/verify`; подтверждение почты не обходится.

## Что остаётся для настоящего запуска Minecraft

1. **Android Java runtime.** Upstream сейчас использует desktop `std::process::Command` и ищет обычный `bin/java`. Нужно подключить ARM64 Android JVM через JNI и управлять её жизненным циклом.
2. **Графика.** Нужны Android Surface + совместимый LWJGL/OpenGL ES/Vulkan backend, framebuffer и обработка потери/восстановления Activity.
3. **Сенсорный ввод.** Нужны экранные кнопки, мульти-тач, мышь/клавиатура/геймпад, обработка системной клавиатуры и паузы приложения.
4. **Файлы.** Реализовать Android Storage Access Framework, URI permissions и app-private storage для импортов, модов, паков и миров.
5. **Проверка совместимости.** Запускать Vanilla, затем отдельные версии Fabric/Quilt/Forge/NeoForge, проверять моды и шейдеры на реальных телефонах.

## Подпись и обновления

CI сейчас генерирует временный test keystore для подписания установочного APK. Это позволяет проверить установку, но новый test keystore на следующей CI-сборке даст другую подпись. Для нормальных обновлений нужен постоянный release keystore, который хранится только в GitHub Secrets, а не в публичном репозитории.

## Лицензии и бренд

Исходный код Millida Launcher — GPL-3.0-only. Upstream [TRADEMARK.md](https://github.com/millida/launcher/blob/main/TRADEMARK.md) требует от публичных форков использовать отличимое название, package ID и графику. Формулировка «неофициальный форк, основанный на Millida Launcher» допустима; наименование приложения «Millida Launcher» и upstream logo — нет. Закрытые ключи и официальные сервисные credentials не копируются.

## Критерий релиза

Успешная компиляция, установка или показ мобильного UI не доказывают запуск Minecraft. Для игрового релиза требуется рабочая ARM64 JVM/JNI, графический backend, сенсорный input bridge, SAF, работающий Vanilla и проверки загрузчиков на Android-устройстве.
