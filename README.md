# dacha video edge computing

Тут описана інтеграція Raspberry PI з IP камерою за протоколом rtsp.
Також описано, як запустити python-додаток, що інтегрується з камерою, як сервіс на Raspbery PI. При цьому сервіс не "падає", якщо підключення до камери не відбулося. Сервіс повторить підключення через заданий інтервал часу.
Конфігурація python-додатку береться з env-змінних. 
Прикладні логи python-додатку пишуться в загальний лог systemctl - що дає можливівсть відслідковувати роботу додатку в реальн
ому часі.
Додаток робить програмну детекцію руху за допомогою бібліотеки open-cv, і, якщо рух виявлено, контурами показую рухомі області кадра і робить запис відеко протягом заданого інтервалу часу (30 секунд).
Записаний відео-файл завантажується на Azure Blob Storage.

## Обладнання для  запуску та тестування

Для запуску та тестування знадобиться IP-камера, яка підтримує rtsp- протокол взаємодії. За звичай, його підтримують камери TP-LINK серії TAPO. В крайньому випадку для тестування та проб підійде мобільний телефон з встановленим додатком ip-camera [pic-01](#pic-01). Тільки треба мати на увазі, що телефони, особливо старі, довго працювати в режимі камери за rptsp протоколом мабуть не мбудуть: то перегріваються, то пам'яті не вистачає. З мого досвіду - ну хвилин на 5-6 безперервної роботи телефону. Але для тестування цього більш ніж достатньо.
Звичайно камера чи телефон та Raspberry PI  повинні бути підключеними до одного і того ж роутера з досупом до інтернету. Доступ до інтернету потрібне, щоб файли завантажувалися у хмару.

<kbd><img src="doc/ipcam.jpg" /></kbd>
<p style="text-align: center;"><a name="pic-01">pic-01</a></p>


## Запуск додатку локально в режимі debug

Зазвичай на Linux ситемах, каталог розробки створюють десь в **/home/username/**. Далі стврюємо каталог **dev** і уже в ньому каталог проекту.
У мене це вигляжає приблизно так:

```text
/home/username/pidev
```
От переходимо в pidev і клонуємо проект з github і отримаємо  там каталог **/dachavideo**. Далі переходимо в каталог, запускаємо Visual Studio Code і далі працюємо уже в цьому середрвищі розробки

```text
cd  /home/username/pidev/dachavideo
code dacha-video.code-workspace
```

Для запуску додатку перш за все треба налаштувати env - змінні в файлі **/.vscode/launch.json**:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python Debugger: vcam_runner.py",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/vcam_runner.py",
      "env": {
        "RTSP_URL": "Налаштувати rtsp URL камери в структурі: rtsp://username:password@host:port/path",
        "AZ_STORAGE_CONNSTRING": "Всановити connect string вашого azure blob storage",
        "AZ_CONTAINER_NAME": "Встановити назву контейнера вашого BlobStorage, куди будуть записуватися файли"

      }
    }
  ]
}

```

 Ну а далі, запускаємо додаток в режимі DEBUG.  і можна дебажити окремі компоненти



## Розгортання додатку, як сервісу

1. Створити  каталог для розгортання
 Linux дозволяє тримати файли де завгодно, але існують загальноприйняті стандарти:

```text


    /opt/назва_проєкту — найкраще місце для стороннього софту, який не є частиною самої ОС. Це ізольовано і чисто.
```

Крім того, потрібно зробити власником каталолога того каористувача під яким буде запускатися сервіс, використовуючи команду chown. Якщо Raspberry PI запускається від імені користувача PI, то я приведу приклад для нього. Хоча я міняв на свою власну обліковку. 

Таким чином, візьмемо назву проекта **camera_monitor**, а запускатися буде від користувача **PI**.
Далі створюємо каталог і міняємо власника.  

```bash
sudo mkdir -p /opt/camera_monitor
sudo chown pi:pi /opt/camera_monitor

```

2. Копіюємо в каталог додатка **/opt/camera_monitor** файли проекта

3. Створюємо файл змінних оточяення **.env** в каталозі додатку

З цього файлу додатко буде брати всі налаштування. Тому створюємо файл за допомогою редактора **nano**,


```bash
sudo nano /opt/camera_monitor/.env
```
та записуємо в нього такі змінні оточекння. Звичайно, їх треба змінити під ваші параметри.

**.env**

```text
RTSP_URL="rtsp://username:password@host:port/path"
AZ_STORAGE_CONNSTRING="azure blob stirage connect string"
AZ_CONTAINER_NAME="azure blob storage container name"
```

4. Традиційно для Python, створюємо віртуальне середовище, активуємо його та встановлюємо в нього необхідні залежності

```bash
cd /opt/camera_monitor
python3 -m venv /opt/camera_monitor/env
source ./env/bin/activate
pip install -r requrements.txt

```

5. Створюємо файл сервіса

Для опису сервісу знову використовуючи реадктор **nano** створюємо файл конфігурації сервісу,

```bash
sudo nano /etc/systemd/system/cameramonitor.service

```

та вписуємо  конфігурацію

```bash
[Unit]
Description=RTSP Camera Monitoring Service
After=network-online.target
Wants=network-online.target

[Service]
# Шлях до папки з проєктом
WorkingDirectory=/opt/camera_monitor
# Вказуємо шлях до нашого файлу зі змінними
EnvironmentFile=/opt/camera_monitor/config.env
# Шлях до Python всередині venv та шлях до самого скрипта
ExecStart=/opt/camera_monitor/env/bin/python /opt/camera_monitor/vcam_runner.py

# Запуск від імені стандартного користувача RPi
User=pi
Group=pi

Restart=always
RestartSec=5

# Дозволяє бачити принти в логах journalctl одразу
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target

```
Тут слід звенути увагу на те, що тепер ми не викристовуємо віртуальне середовище, а просто запускаємо python з каталога віртуального середовища.
Щоб бачити вивід  Python-скрипта прямо в логах systemctl — заслуга параметра Environment=PYTHONUNBUFFERED=1, який додано в конфігурацію. Без нього Python міг би накопичувати текст у буфері й видавати його пачками, а не в реальному часі.
І в цьому файлі змннних **Environment=** можна задати стільки, скільки потрібно. Але, як на мене, то краще задавати змінні в файлі .env **EnvironmentFile=/opt/camera_monitor/.env**  

5. Запуск сервіса

Для запуску сервіса послідовно виконуємо таку послідовність команд

```bash
sudo systemctl daemon-reload
sudo systemctl enable cameramonitor.service
sudo systemctl start cameramonitor.service
```

6. Подивитися логи роботи сервіса

Тепер перевіримо, що сервіс дійсно працює, шляхом перегляду "живого" лога його роботи 

```bash
journalctl -u cameramonitor.service -f

```
-f  вказує на те, що показувати лог в режимі реального часу

7. Зупинка сервісу

Зупинка сервісу виконується командою:

```bash
sudo systemctl stop cameramonitor.service

```

І знову треба перевірити логи, що сервіс зупинився:

```bash
journalctl -u cameramonitor.service -f

```

8. Дії, коли файл конфігурації сервісу треба змінити

Якщо виникла необхідність внести зміни у файл конфігурації сервісу (той, що /etc/systemd/system/cameramonitor.service),  потрібно виконати два кроки, щоб система їх побачила і застосувала:

- Оновити конфігурацію systemd

Система зчитує файли сервісів у пам'ять лише під час завантаження або за спеціальною командою. Щоб вона помітила  правки у файлі .service, потрібно виконати:

```bash
sudo systemctl daemon-reload
```

- Перезапустити сервіс

Команда daemon-reload лише оновлює "план дій" в пам'яті системи, але не зупиняє поточний процес. Щоб  скрипт почав працювати за новими правилами, його треба перезавантажити:

```bash
sudo systemctl restart cameramonitor.service
```

**Важливе уточнення:**

- Якщо ви змінили тільки файл .service (наприклад, змінили шлях до файлу, додали змінну оточення Environment або змінили таймер RestartSec): потрібно робити і daemon-reload, і restart.

- Якщо ви змінили тільки код самого Python-скрипта (vcam_wrkr.py): daemon-reload робити не потрібно. Достатньо просто виконати sudo systemctl restart cameramonitor.service, щоб скрипт перечитався з диска.

**Як перевірити, що все пройшло успішно?**

Після перезапуску завжди корисно заглянути в статус:

```bash
sudo systemctl status cameramonitor.service

```

Там можна побачите, чи не виникло помилок у самому файлі конфігурації (наприклад, якщо десь допустили помилку в синтаксисі).

Якщо виникає необхідність часто правити код і потрібно бачити логи в реальному часі під час перезапуску, тримайте відкритим друге вікно терміналу з командою:

```bash

journalctl -u cameramonitor.service -f

```
Вона покаже момент зупинки і нового старту скрипта.


## Корисні команди для роботи з логами


1. Тільки помилки: Якщо скрипт працює тиждень і логів забагато, можна вивести тільки повідомлення про помилки:

```bash
journalctl -u cameramonitor.service -p err
```

2. Логи за певний час: Подивитися, що відбувалося з камерою вранці:

```bash

journalctl -u cameramonitor.service --since "2024-05-20 08:00:00" --until "2024-05-20 10:00:00"

```

2. Очищення (якщо логи зайняли багато місця): Зазвичай система сама їх чистить, але вручну можна так:

```bash

    sudo journalctl --vacuum-time=2d  # залишити логи лише за останні 2 дні
```

3. Видалити все, крім останніх 5 хвилин:

```bash

sudo journalctl --vacuum-time=5m

```
4. Залишити лише останні 100 мегабайт логів:

```bash
sudo journalctl --vacuum-size=100M

```

5. Видалити все, крім логів за сьогодні:

```bash
    sudo journalctl --vacuum-time=1d
```

6. Як «обнулити» лог для зручного читання


Якщо  зараз налагоджуємо сервіс і хочеться, щоб команда journalctl -u cameramonitor.service -f показувала тільки нові записи, які з'являться після цього моменту, використовуємо прапорець -b (тільки з моменту останнього завантаження системи) або --since:

- *Показувати логи лише з моменту останнього старту системи*:
 
 ```bash
journalctl -u cameramonitor.service -b
```

- *Показувати лише «свіжі» логи (наприклад, за останні 2 хвилини)*:

```bash
    journalctl -u cameramonitor.service --since "2 minutes ago" -f
```

7. Автоматичне обмеження логів

Щоб логи камери не забили всю SD-карту Raspberry Pi з часом, краще обмежити розмір журналу в конфігурації самої системи.

*Відкрийте файл налаштувань*:

```bash
sudo nano /etc/systemd/journald.conf
```

*Знайдіть (або додайте) рядок SystemMaxUse*:
Ini, TOML

```text
SystemMaxUse=200M
```
Це обмежить загальний розмір усіх логів у системі до 200 МБ. Для Raspberry Pi це оптимальне значення).

Перезапустіть службу логів:

```bash
sudo systemctl restart systemd-journald
```

Лайфхак для розробки

Якщо ви хочете повністю очистити всі системні логи (включаючи ваш сервіс) прямо зараз, щоб почати "з чистого аркуша":

```bash
sudo journalctl --rotate
sudo journalctl --vacuum-time=1s
```

Команда --rotate закриває поточні файли логів і створює нові, а --vacuum-time=1s видаляє все, що було записано раніше цієї секунди.


## Приклад логу systemctl

```log

psh@raspberrypi:~ $ sudo nano /etc/systemd/system/cameramonitor.service
psh@raspberrypi:~ $ sudo systemctl daemon-reload
psh@raspberrypi:~ $ sudo systemctl restart cameramonitor.service
psh@raspberrypi:~ $ sudo systemctl status cameramonitor.service
● cameramonitor.service - RTSP Camera Monitoring Service
     Loaded: loaded (/etc/systemd/system/cameramonitor.service; enabled; preset: enabled)
     Active: active (running) since Mon 2025-12-29 15:55:20 EET; 11s ago
 Invocation: a4c90194f8e34ad18cc3cc5a09e91172
   Main PID: 7916 (python)
      Tasks: 4 (limit: 9566)
        CPU: 547ms
     CGroup: /system.slice/cameramonitor.service
             └─7916 /opt/camera_monitor/env/bin/python /opt/camera_monitor/vcam_runner.py

Dec 29 15:55:20 raspberrypi systemd[1]: Started cameramonitor.service - RTSP Camera Monitoring Service.
Dec 29 15:55:20 raspberrypi python[7916]: 2025-12-29 15:55:20,754 - DEBUG - vcam_worker.vcam_wrkr - debug message
Dec 29 15:55:20 raspberrypi python[7916]: 2025-12-29 15:55:20,754 - DEBUG - vcam_worker.vcam_wrkr - ===================================
Dec 29 15:55:20 raspberrypi python[7916]: 2025-12-29 15:55:20,754 - DEBUG - vcam_worker.vcam_wrkr - ===================================
Dec 29 15:55:20 raspberrypi python[7916]: 2025-12-29 15:55:20,754 - DEBUG - vcam_worker.vcam_wrkr - Читаю налаштування
Dec 29 15:55:20 raspberrypi python[7916]: [tcp @ 0x3f98e760] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 15:55:20 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
Dec 29 15:55:31 raspberrypi python[7916]: [tcp @ 0x3f98e760] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 15:55:31 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
psh@raspberrypi:~ $ sudo systemctl stop cameramonitor.service
psh@raspberrypi:~ $ 



c 29 15:57:51 raspberrypi python[7916]: 2025-12-29 15:57:51,590 - DEBUG - vcam_worker.vcam_wrkr - Завантаження завершено!
Dec 29 15:57:51 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Завантаження завершено!
Dec 29 15:57:51 raspberrypi python[7916]: 2025-12-29 15:57:51,593 - DEBUG - vcam_worker.vcam_wrkr - Локальний файл 20251229-155720.avi видалено.
Dec 29 15:57:51 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Локальний файл 20251229-155720.avi видалено.
Dec 29 15:58:07 raspberrypi python[7916]: 2025-12-29 15:58:07,796 - DEBUG - vcam_worker.vcam_wrkr - Рух виявлено! Початок запису.
Dec 29 15:58:07 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Рух виявлено! Початок запису.
Dec 29 15:58:37 raspberrypi python[7916]: 2025-12-29 15:58:37,909 - DEBUG - vcam_worker.vcam_wrkr - Запис завершено.
Dec 29 15:58:37 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Запис завершено.
Dec 29 15:58:38 raspberrypi python[7916]: 2025-12-29 15:58:38,158 - DEBUG - vcam_worker.vcam_wrkr -
Dec 29 15:58:38 raspberrypi python[7916]: Завантаження файлу 20251229-155807.avi до блобу 20251229-155807.avi...
Dec 29 15:58:38 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:
Dec 29 15:58:38 raspberrypi python[7916]: Завантаження файлу 20251229-155807.avi до блобу 20251229-155807.avi...
Dec 29 15:58:39 raspberrypi python[7916]: 2025-12-29 15:58:39,400 - DEBUG - vcam_worker.vcam_wrkr - Завантаження завершено!
Dec 29 15:58:39 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Завантаження завершено!
Dec 29 15:58:39 raspberrypi python[7916]: 2025-12-29 15:58:39,402 - DEBUG - vcam_worker.vcam_wrkr - Локальний файл 20251229-155807.avi видалено.
Dec 29 15:58:39 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Локальний файл 20251229-155807.avi видалено.
Dec 29 15:58:55 raspberrypi python[7916]: 2025-12-29 15:58:55,669 - DEBUG - vcam_worker.vcam_wrkr - Рух виявлено! Початок запису.
Dec 29 15:58:55 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Рух виявлено! Початок запису.
Dec 29 15:59:25 raspberrypi python[7916]: 2025-12-29 15:59:25,720 - DEBUG - vcam_worker.vcam_wrkr - Запис завершено.
Dec 29 15:59:25 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Запис завершено.
Dec 29 15:59:26 raspberrypi python[7916]: 2025-12-29 15:59:26,002 - DEBUG - vcam_worker.vcam_wrkr -
Dec 29 15:59:26 raspberrypi python[7916]: Завантаження файлу 20251229-155855.avi до блобу 20251229-155855.avi...
Dec 29 15:59:26 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:
Dec 29 15:59:26 raspberrypi python[7916]: Завантаження файлу 20251229-155855.avi до блобу 20251229-155855.avi...
Dec 29 15:59:29 raspberrypi python[7916]: 2025-12-29 15:59:29,531 - DEBUG - vcam_worker.vcam_wrkr - Завантаження завершено!
Dec 29 15:59:29 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Завантаження завершено!
Dec 29 15:59:29 raspberrypi python[7916]: 2025-12-29 15:59:29,534 - DEBUG - vcam_worker.vcam_wrkr - Локальний файл 20251229-155855.avi видалено.
Dec 29 15:59:29 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Локальний файл 20251229-155855.avi видалено.
Dec 29 16:00:20 raspberrypi python[7916]: 2025-12-29 16:00:20,472 - DEBUG - vcam_worker.vcam_wrkr - Рух виявлено! Початок запису.
Dec 29 16:00:20 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Рух виявлено! Початок запису.
Dec 29 16:00:30 raspberrypi python[7916]: WARNING:root:Потік перервався. Спроба перепідключення...
Dec 29 16:00:30 raspberrypi python[7916]: [tcp @ 0x405344c0] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 16:00:30 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
Dec 29 16:00:40 raspberrypi python[7916]: [tcp @ 0x405344c0] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 16:00:40 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
Dec 29 16:00:50 raspberrypi python[7916]: [tcp @ 0x405344c0] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 16:00:50 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
Dec 29 16:01:00 raspberrypi python[7916]: [tcp @ 0x405344c0] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 16:01:00 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
Dec 29 16:01:16 raspberrypi python[7916]: 2025-12-29 16:01:16,000 - DEBUG - vcam_worker.vcam_wrkr - Рух виявлено! Початок запису.
Dec 29 16:01:16 raspberrypi python[7916]: DEBUG:vcam_worker.vcam_wrkr:Рух виявлено! Початок запису.
Dec 29 16:01:21 raspberrypi python[7916]: WARNING:root:Потік перервався. Спроба перепідключення...
Dec 29 16:01:21 raspberrypi python[7916]: [tcp @ 0x405347b0] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 16:01:21 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
Dec 29 16:01:31 raspberrypi python[7916]: [tcp @ 0x405347b0] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 16:01:31 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
Dec 29 16:01:41 raspberrypi python[7916]: [tcp @ 0x405347b0] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 16:01:41 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
Dec 29 16:01:51 raspberrypi python[7916]: [tcp @ 0x405347b0] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 16:01:51 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
Dec 29 16:02:02 raspberrypi python[7916]: [tcp @ 0x405347b0] Connection to tcp://192.168.0.101:8554?timeout=0 failed: Connection refused
Dec 29 16:02:02 raspberrypi python[7916]: ERROR:root:Камера недоступна. Наступна спроба через 10 секунд.
Dec 29 16:02:12 raspberrypi systemd[1]: Stopping cameramonitor.service - RTSP Camera Monitoring Service...
Dec 29 16:02:12 raspberrypi systemd[1]: cameramonitor.service: Deactivated successfully.
Dec 29 16:02:12 raspberrypi systemd[1]: Stopped cameramonitor.service - RTSP Camera Monitoring Service.
Dec 29 16:02:12 raspberrypi systemd[1]: cameramonitor.service: Consumed 17.347s CPU time.


```