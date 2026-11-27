from django.core.management.base import BaseCommand
from support.models import FAQ


class Command(BaseCommand):
    help = 'Add verified service FAQ without overwriting administrator edits. Live monetary rules come from backend context.'

    def handle(self, *args, **options):
        entries = [
            ('verified-checkout', 'Как оформить заказ?', 'Выберите ресторан и блюда, откройте корзину, укажите адрес и способ оплаты. Сумму, промокод и допустимое списание бонусов проверяет сервер.',
             'How do I place an order?', 'Choose a restaurant and dishes, open the cart, enter an address and payment method. The server verifies prices, promo and allowed bonus redemption.',
             'Тапсырысты қалай беремін?', 'Мейрамхана мен тағамдарды таңдап, себетті ашыңыз. Мекенжай мен төлем тәсілін көрсетіңіз. Баға, промокод пен бонусты сервер тексереді.'),
            ('verified-payment', 'Как проверить оплату?', 'Откройте раздел «Платежи». Онлайн-оплату подтверждает сервер после проверки у провайдера. Возвращение на сайт само по себе не означает успешную оплату. Не вводите данные карты в чат.',
             'How do I check payment?', 'Open Payments. The backend confirms online payment with the provider. Returning to the website alone does not mean payment succeeded. Never enter card details in chat.',
             'Төлемді қалай тексеремін?', '«Төлемдер» бөлімін ашыңыз. Онлайн төлемді сервер провайдерден тексерген соң растайды. Сайтқа оралу төлемнің сәтті болғанын білдірмейді. Карта деректерін чатқа жазбаңыз.'),
            ('verified-cashback', 'Где посмотреть бонусы?', 'Доступный баланс и история операций находятся в профиле. В корзине сервер показывает лимит списания и прогноз начисления. Доставка бонусами не оплачивается. Актуальные проценты и условия помощник получает с сервера.',
             'Where can I see my bonuses?', 'Your profile shows available bonuses and ledger history. The cart displays the server spending limit and earnings forecast. Bonuses do not pay for delivery. Current rates and terms are read from backend settings.',
             'Бонустарды қайдан көремін?', 'Қолжетімді бонус пен операциялар тарихы профильде көрсетіледі. Себетте сервер есептеген шек пен болжам бар. Жеткізуге бонус жұмсалмайды. Ағымдағы шарттар серверден алынады.'),
            ('verified-reviews', 'Как исправить отзыв?', 'В разделе «Заказы» найдите свой отзыв и нажмите «Редактировать». После изменения он снова проходит модерацию и временно не публикуется. Причину отклонения видит автор. Обычная негативная оценка разрешена.',
             'How do I edit a review?', 'Find your review in Orders and select Edit. An edited review is hidden until moderation approves it again. Its author can see the rejection reason. Ordinary negative feedback is allowed.',
             'Пікірді қалай түзетемін?', '«Тапсырыстар» бөлімінен өз пікіріңізді тауып, «Өңдеу» батырмасын басыңыз. Өзгерген пікір модерацияға жіберіліп, мақұлданғанша жарияланбайды. Бас тарту себебі авторға көрінеді.'),
        ]
        created = 0
        entries.extend([
            ('verified-project-overview', 'Что умеет JetFood и как работает приложение?',
             'JetFood — доставка еды: регистрация и вход, каталог ресторанов и их отдельных меню, корзина одного ресторана, серверная проверка цены и промокода, доставка, оплата, отзывы с модерацией и JetPoints. Заказы и их статусы — в «Заказы», история оплаты — в «Платежи», адреса и бонусы — в «Мой профиль». Онлайн-оплата доступна только при настройке провайдера. Сотрудники управляют приготовлением, доставкой и запросами клиентов в пределах своей роли. Для помощи есть чат ИИ, FAQ и создание обращения. Чат читает только разрешённые данные вашего аккаунта и сам не проводит финансовые операции.',
             'What does JetFood do and how does the application work?',
             'JetFood provides registration/login, restaurants with individual menus, a single-restaurant cart, backend price/promo validation, delivery, payments, moderated reviews and JetPoints. Orders shows order statuses, Payments shows payment history, and My profile contains addresses and rewards. Online payment requires a configured provider. Staff manage preparation, delivery and customer requests within their role. Help includes AI chat, FAQ and support requests. Chat reads only permitted account data and performs no financial actions.',
             'JetFood не істейді және қолданба қалай жұмыс істейді?',
             'JetFood-та тіркелу және кіру, мейрамханалар мен жеке мәзірлер, бір мейрамхананың себеті, баға мен промокодты серверде тексеру, жеткізу, төлем, тексерілетін пікірлер және JetPoints бар. Күйлер «Тапсырыстарда», төлем тарихы «Төлемдерде», мекенжайлар мен бонустар «Менің профилімде». Онлайн төлем үшін провайдер бапталуы қажет. Қызметкерлер өз рөлі шегінде дайындауды, жеткізуді және өтініштерді басқарады. Көмек үшін AI чат, FAQ және қолдауға өтініш жасау бар. Чат тек рұқсат етілген аккаунт деректерін оқиды және қаржылық әрекет орындамайды.'),
            ('verified-registration', 'Как зарегистрироваться без телефона и email?',
             'Откройте «Регистрация», укажите имя пользователя, пароль минимум из 8 символов и повторите пароль. Email и телефон необязательны: оба поля можно оставить пустыми. Если заполняете их, формат проверяется. Вход выполняется по имени пользователя и паролю, не по email.',
             'How do I register or sign up without email or phone?',
             'Open Register. Choose a username and a password of at least 8 characters, then repeat the password. Email and phone are BOTH optional and may both be empty. If supplied, their format is checked. Sign in with username and password, not email.',
             'Телефонсыз және электрондық поштасыз қалай тіркелемін?',
             '«Тіркелу» бетін ашып, пайдаланушы атын, кемінде 8 таңбалы құпиясөзді енгізіп, оны қайталаңыз. Электрондық пошта мен телефон міндетті емес: екеуін де бос қалдыруға болады. Толтырсаңыз, пішімі тексеріледі. Кіру үшін пайдаланушы аты мен құпиясөз қажет.'),
            ('verified-cash-jetpoints', 'Тапсырыс жеткізілді, неге JetPoints түспеді?',
             'JetPoints начисляются только после подтверждённой оплаты и доставки. Получение наличных подтверждает назначенный курьер, менеджер или администратор: «Заказы» → «Подробнее» → «Подтвердить получение наличных»; также доступен раздел «Платежи». Клиент не может подтвердить собственную оплату. Баланс обновляется каждые 30 секунд или при возвращении в окно. Одна доставка не подтверждает получение денег.',
             'My order was delivered. Why did I not receive JetPoints?',
             'JetPoints require BOTH confirmed payment and delivery. For cash orders, the assigned courier, manager or admin must confirm cash receipt in Orders > Details > Confirm cash received (also available in Payments). A customer cannot confirm their own payment. Balance refreshes every 30 seconds or on window focus. Delivery alone does not prove that cash was collected.',
             'Тапсырыс жеткізілді, JetPoints неге түспеді?',
             'JetPoints төлем расталып, тапсырыс жеткізілгенде ғана есептеледі. Қолма-қол төлемді тағайындалған курьер, менеджер немесе әкімші «Тапсырыстар» → «Толығырақ» → «Қолма-қол ақшаның алынғанын растау» арқылы растайды. Клиент өз төлемін растай алмайды. Баланс 30 секунд сайын немесе терезеге оралғанда жаңарады.'),
            ('verified-loyalty-levels', 'Какие уровни и условия JetPoints, как тратить бонусы?',
             '1 JetPoint равен 1 тенге. Проценты, текущий уровень, пороги заказов, лимит списания и бонус второго заказа берутся из действующих настроек сервера. Уровень зависит от оплаченных доставленных заказов текущего календарного месяца по времени Казахстана. Скидки и списанные бонусы уменьшают базу начисления; доставка в неё не входит. Баланс, прогресс уровня, срок второго заказа и журнал операций доступны в профиле. Отмена и возврат пересчитывают соответствующие бонусы. Бонусы не сгорают.',
             'What are JetPoints levels, cashback rules and spending limits?',
             '1 JetPoint equals 1 KZT. Read current rates, tier thresholds, spending limits and second-order offer from live backend policy. Levels count paid and delivered orders in the current Kazakhstan calendar month. Discounts and redeemed points reduce earnings; delivery is excluded. Profile shows balance, tier progress, second-order deadline and ledger. Cancellations and refunds adjust corresponding rewards. Points do not expire.',
             'JetPoints деңгейлері, кэшбэк және ұпай жұмсау шарттары қандай?',
             '1 JetPoint = 1 теңге. Мөлшерлемелер, деңгей шектері, жұмсау лимиті мен екінші тапсырыс сыйақысы сервердің ағымдағы баптауларынан алынады. Деңгей осы күнтізбелік айдағы Қазақстан уақытымен төленіп, жеткізілген тапсырыстарға байланысты. Жеңілдіктер мен жұмсалған бонустар есептеу сомасын азайтады; жеткізу есепке кірмейді. Баланс пен операциялар тарихы профильде. Ұпайлардың мерзімі шектелмеген.'),
            ('verified-catalog-gaps', 'Сколько стоят блюда и бургеры в ресторане, если меню пустое?',
             'Цены, состав меню и доступность сообщаются только из базы выбранного ресторана. Если меню ещё не загружено, подтверждённых цен нет. Нельзя подставлять блюда или цены другого ресторана. Пустая база меню не означает, что заведение не продаёт еду. Если часы работы не указаны, они неизвестны. Выберите ресторан с загруженным меню или создайте обращение в поддержку.',
             'What do dishes or burgers cost when a restaurant menu is empty?',
             'Use only dishes, prices and availability stored for the selected restaurant. An empty menu means verified prices are unavailable, not that the restaurant sells no food. Never substitute another restaurant menu or price. Missing opening hours are unknown. Choose a restaurant with a loaded menu or create a support request.',
             'Мейрамхана мәзірі бос болса, тағамдар мен бургерлер қанша тұрады?',
             'Тек таңдалған мейрамхананың базадағы мәзірін, бағасын және қолжетімділігін қолданыңыз. Бос мәзір расталған бағалардың жоқтығын білдіреді, мейрамханада тамақ жоқ деген сөз емес. Басқа мейрамхананың тағамы мен бағасын қолдануға болмайды. Көрсетілмеген жұмыс уақыты белгісіз. Мәзірі жүктелген мейрамхананы таңдаңыз немесе қолдауға өтініш жасаңыз.'),
            ('verified-order-actions', 'Как отменить заказ или запросить возврат?',
             'Откройте «Заказы» и действия нужного заказа. Доступное действие зависит от статуса заказа и оплаты: мгновенная отмена ожидающего заказа с причиной либо запрос на отмену или возврат. Запрос рассматривает менеджер или администратор; он может одобрить или отклонить его. Отправка запроса не означает возврат денег. Чат ИИ сам не выполняет отмену, возврат или оплату и не обещает их успех.',
             'How do I cancel an order or request a refund?',
             'Open Orders and the relevant order actions. Availability depends on order/payment status: immediate pending-order cancellation with a reason, or a cancellation/refund request. A manager or admin reviews and may approve or reject a request. Submitting one does not mean money was refunded. AI chat cannot perform cancellation, refund or payment and cannot promise success.',
             'Тапсырыстан қалай бас тартамын немесе ақшаны қайтаруды сұраймын?',
             '«Тапсырыстар» бөлімінде қажетті тапсырыстың әрекеттерін ашыңыз. Қолжетімді әрекет тапсырыс пен төлем күйіне байланысты: күтілудегі тапсырыстан себебін көрсетіп бас тарту немесе бас тарту не қайтару туралы өтініш. Оны менеджер не әкімші қарап, мақұлдайды немесе қабылдамайды. Өтініш жіберу ақшаның қайтқанын білдірмейді. AI чат бұл әрекеттерді орындамайды.'),
            ('verified-promo-rules', 'Почему не работает промокод WELCOME или AINUR?',
             'Введите код латиницей, без пробелов по краям; регистр не важен. Актуальные вид, размер, срок, ресторан, минимальная сумма и лимит на аккаунт берутся из базы промокодов. Чтобы объяснить конкретный отказ, нужны код, ресторан и сумма товаров. Предпросмотр не расходует применение. У заказа один промокод, применённый при создании; отмена заказа не возвращает использование. Статус оплаты нельзя определять по факту применения кода.',
             'Why does my WELCOME or AINUR promo code not work?',
             'Enter the Latin code with no surrounding spaces; case does not matter. Read current discount type/value, dates, restaurant, minimum subtotal and account usage limit from the promo database. Diagnose using code, restaurant and merchandise subtotal. Preview does not consume usage. One promo applies per order at creation; cancellation does not restore usage. Promo application does not prove payment.',
             'WELCOME немесе AINUR промокоды неге жұмыс істемейді?',
             'Кодты латын әріптерімен, шеттерінде бос орынсыз енгізіңіз; әріп регистрі маңызды емес. Жеңілдік түрі, мөлшері, мерзімі, мейрамхана, ең төменгі сома және аккаунт лимиті промокодтар базасынан алынады. Нақты мәселе үшін код, мейрамхана және тауар сомасы қажет. Алдын ала есептеу лимитті жұмсамайды. Бір тапсырысқа бір промокод қолданылады; бас тарту қолданылған лимитті қайтармайды.'),
            ('verified-profile-help', 'Как изменить адрес, пароль или данные аккаунта?',
             'Откройте «Мой профиль»: там редактируются личные данные, сохранённые адреса доставки и пароль. В корзине можно выбрать сохранённый адрес или ввести адрес доставки. Не сообщайте чату пароль, токен, CVV, номер карты или SMS-код. Помощник может объяснить шаги, но не меняет эти данные за вас.',
             'How do I change my address, password or account details?',
             'Open My profile to edit personal information, saved delivery addresses and password. At checkout choose a saved address or enter a delivery address. Never share passwords, tokens, CVV, card numbers or SMS codes in chat. The assistant explains steps but does not change these details for you.',
             'Мекенжайды, құпиясөзді немесе аккаунт деректерін қалай өзгертемін?',
             'Жеке мәліметтерді, сақталған мекенжайларды және құпиясөзді өзгерту үшін «Менің профилім» бөлімін ашыңыз. Себетте сақталған мекенжайды таңдауға немесе жаңасын енгізуге болады. Чатқа құпиясөз, токен, CVV, карта нөмірі не SMS-код жазбаңыз. Көмекші әрекеттерді түсіндіреді, бірақ деректерді сіздің орныңызға өзгертпейді.'),
        ])
        for slug, qr, ar, qe, ae, qk, ak in entries:
            _, new = FAQ.objects.get_or_create(slug=slug, defaults=dict(question_ru=qr, answer_ru=ar, question_en=qe, answer_en=ae, question_kk=qk, answer_kk=ak))
            created += new
        self.stdout.write(f'Created {created} FAQ entries; existing edits preserved.')
