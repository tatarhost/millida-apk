# Матрица функций настоящего Android-порта Millida

Пока нет функции, которую можно честно отметить как «перенесена и протестирована на Android». Этот список описывает реальные разделы upstream `millida/launcher` и критерии их мобильного переноса, а не заявляет, что их уже содержит опубликованный APK.

| Функция исходного Millida Launcher | Android-перенос | Что требуется |
|---|---|---|
| React UI / навигация | Не перенесено | Тот же UI исходника, адаптивная раскладка и touch |
| Профили и сборки | Не перенесено | Rust IPC + app-private storage |
| Vanilla Minecraft | Не перенесено | Android ARM64 JVM через JNI и GLES/Vulkan/LWJGL |
| Java runtime management | Не перенесено | Android runtime packages, не desktop JRE |
| Fabric / Quilt | Не проверено | Установка и запуск реальных версий на Android |
| Forge / NeoForge | Не проверено | Отдельные проверки по версии Minecraft |
| Моды / Modrinth / CurseForge | Не перенесено | Сохранить исходные загрузчики и адаптировать SAF |
| ZIP / MRPACK / packwiz | Не перенесено | Android file picker и безопасная распаковка |
| Ресурспаки / шейдеры | Не проверено | Проверить конкретный mobile renderer и GPU |
| Миры / резервные копии | Не перенесено | SAF, URI permissions и private storage |
| Серверы / Quick Play | Не перенесено | Android network lifecycle и сохранение серверов |
| Microsoft sign-in | Не перенесено | Собственная OAuth app registration/redirect |
| Скины / плащи / аккаунт Millida | Ограничено | Только с разрешёнными сервисами/учётными данными |
| Друзья / чат / голос | Не перенесено | Проверить сервисы, разрешения и Android audio lifecycle |
| Хостинг / серверные разделы | Не перенесено | Проверить API-права и работу экранов |
| Desktop tray | Не применимо | Android notification/foreground service при необходимости |
| Global hotkeys | Не применимо | Экранные controls и поддержка клавиатуры/геймпада |
| Desktop in-game overlay | Не применимо | Android control overlay / встроенные игровые контролы |
| Desktop auto-updater | Не применимо | Android APK/AAB distribution и установочный flow |

Правило: функция становится «перенесена» только после запуска и проверки на реальном Android устройстве. Один лишь успешный web-build, видимая кнопка или компиляция Rust не доказывают, что функция работает.
