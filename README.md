# CHEATLAB Launcher для Android

Неофициальная мобильная адаптация интерфейса и ядра проекта [Millida Launcher](https://github.com/millida/launcher), с интеграцией аккаунта **CHEATLAB**.

<badge>Android-порт в разработке</badge>

Этот проект использует исходники Millida под GPL-3.0-only, но не является официальной сборкой Millida. Публичный форк имеет собственное название, application ID, логотип и интеграцию с сайтом [cheatlab.fun](https://cheatlab.fun).

## Вход

При первом запуске приложение предлагает войти или зарегистрироваться на **cheatlab.fun**. Приложение создаёт короткоживущую ссылку; после входа на сайте пользователь подтверждает подключение, а приложение получает отдельную сессию, связанную с установкой. Сессия хранится в зашифрованном нативном хранилище Rust и не помещается в localStorage браузера.

Также предусмотрен вход по ключу аккаунта CHEATLAB формата `clab2-…`. После ввода ключа требуется код подтверждения из письма. Создать такой ключ можно на сайте: [cheatlab.fun/launcher-key.html](https://cheatlab.fun/launcher-key.html).

Вход CHEATLAB не заменяет игровой аккаунт Minecraft. После подключения CHEATLAB пользователь отдельно выбирает Microsoft или офлайн-ник.

## Что добавлено для Android

- собственное название **CHEATLAB Launcher** и новая иконка;
- нижняя панель навигации для телефона;
- скрытие desktop titlebar и боковой панели на узких экранах;
- безопасные отступы под вырезы экрана, прокрутка и touch-friendly controls;
- вход через браузер по device-link с возвратом в приложение;
- вход через ключ CHEATLAB и email OTP;
- шифрованное хранение сессии на стороне Rust.

## Что ещё не готово

Успешная сборка и установка APK не означают, что Minecraft уже запускается на Android. Upstream-ядро пока использует desktop Java process model через `std::process::Command`. Для настоящего игрового запуска нужно добавить Android ARM64 JVM через JNI, совместимый графический backend и передачу сенсорного ввода. Также отдельно требуется Android Storage Access Framework для файлов/модов/миров.

## Документы

- [PORTING.md](PORTING.md) — архитектура и оставшиеся этапы.
- [FEATURES.md](FEATURES.md) — матрица функций и проверок.
- [ANDROID_BUILD_STATUS.md](ANDROID_BUILD_STATUS.md) — фактический статус CI.
- [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) — лицензии и сторонние компоненты.

## Бренд и лицензия

Код upstream Millida Launcher распространяется под GPL-3.0-only. Согласно upstream [TRADEMARK.md](https://github.com/millida/launcher/blob/main/TRADEMARK.md), GPL не даёт права распространять форк под именем или логотипом Millida. Поэтому приложение называется CHEATLAB Launcher и указывает, что основано на Millida. Официальные ключи подписи, Microsoft/Discord app IDs и приватные сервисные credentials не копируются.
