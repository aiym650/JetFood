"""Verified service/account tool results. No arbitrary SQL, URLs or mutations."""
import re
from django.conf import settings
from django.utils import timezone

from loyalty.amounts import display
from loyalty.models import LoyaltyPolicy
from loyalty.views import account_data
from orders.models import Order, PromoCode, PromoRedemption
from payments.freedompay import configured
from users.models import User
from .assistant import redact_support_text
from .models import FAQ
from .order_lookup import resolve_order


def service_answer(case, conversation):
    questions = [row['body'] for row in conversation if row['sender'] == 'customer'][-3:]
    if not questions:
        return None
    text = questions[-1]
    language = case.language
    index = {'ru': 0, 'en': 1, 'kk': 2}[language]

    def t(ru, en, kk):
        return (ru, en, kk)[index]

    def matches(pattern):
        return bool(re.search(pattern, text, re.I))

    sections = []
    articles = []
    if matches(r'дамп|dump|всю\s+баз|всех\s+пользоват|all\s+users|чуж(?:ой|ого|ие)|another\s+(?:user|customer)|басқа\s+пайдаланушы'):
        return t('Помощник читает актуальный публичный каталог и данные только вашего аккаунта. Чужие заказы, пароли, токены и полный дамп базы недоступны. Можно спросить о меню, своём заказе, оплате, JetPoints, промокодах и правилах сервиса.', 'The assistant reads the live public catalog and only your own account data. Other customers\' orders, passwords, tokens and full database dumps are unavailable. Ask about menus, your order/payment, JetPoints, promos or service rules.', 'Көмекші ағымдағы ашық каталог пен тек өз аккаунтыңыздың деректерін оқиды. Басқа клиенттердің тапсырыстары, құпиясөздер, токендер және толық база көшірмесі қолжетімсіз. Мәзір, өз тапсырысыңыз, төлем, JetPoints, промокод пен қызмет ережелері туралы сұраңыз.')
    points = matches(r'jetpoint|кэшб|кешб|бонус|баланс|балл|cashback|loyalty|balance|points|ұпай')
    promo = matches(r'промокод|promo|welcome|ainur|жеңілдік\s*код')
    short_followup = len(text.split()) <= 9 and matches(r'^(?:а\b|and\b|what about\b|ал\b)')
    if short_followup and len(questions) > 1:
        points = points or bool(re.search(r'jetpoint|кэшб|бонус|cashback|loyalty|ұпай', questions[-2], re.I))
        promo = promo or bool(re.search(r'промокод|promo|welcome|ainur', questions[-2], re.I))
    payment_question = matches(r'оплат|плат[её]ж|payment|cash\b|төлем|қолма')
    order_question = matches(r'где.*заказ|статус.*заказ|заказ.*статус|мой\s+заказ|моего\s+заказ|последн\w*\s+заказ|order.*status|where.*order|my.*order|(?:latest|last)\s+order|тапсырыс.*(?:күй|қайда)|менің.*тапсырыс')
    explicit_number = matches(r'\bORD[-_]|\b[\w-]+-ORDER\b|(?:заказ(?:а|у)?|order|тапсырыс)\s*[№#]?\s*\d')
    if order_question or explicit_number or (payment_question and (getattr(case, 'order_id', None) or matches(r'статус|прош|поступ|успеш|status|success|paid|растал'))) or (points and matches(r'не.*(?:начисл|приш|меня|обновл|түс)|not.*(?:earn|receive|updat)|доставлен')):
        order, explicit = resolve_order(case, conversation)
        if order is None:
            if explicit:
                sections.append(t('Этот заказ недоступен в вашем аккаунте. Проверьте номер своего заказа в разделе «Заказы».', 'This order is unavailable in your account. Check your own order number in Orders.', 'Бұл тапсырыс аккаунтыңызда қолжетімсіз. «Тапсырыстар» бөлімінен өз нөміріңізді тексеріңіз.'))
            else:
                recent = list(Order.objects.filter(customer_id=case.customer_id).order_by('-created_at', '-id').values_list('order_number', flat=True)[:3])
                sections.append(t('Укажите номер заказа или привяжите свой заказ к беседе.', 'Please give an order number or link your own order to this conversation.', 'Тапсырыс нөмірін көрсетіңіз немесе өз тапсырысыңызды әңгімеге байланыстырыңыз.') + ('\n' + ', '.join(recent) if recent else ''))
        else:
            statuses = {
                'pending': t('ожидает подтверждения', 'awaiting confirmation', 'растау күтілуде'),
                'confirmed': t('подтверждён', 'confirmed', 'расталды'),
                'preparing': t('готовится', 'preparing', 'дайындалуда'),
                'ready_for_pickup': t('готов к передаче курьеру', 'ready for pickup', 'курьерге беруге дайын'),
                'delivering': t('в пути', 'on the way', 'жолда'),
                'delivered': t('доставлен', 'delivered', 'жеткізілді'),
                'cancelled': t('отменён', 'cancelled', 'күші жойылды'),
            }
            pay_labels = {
                'pending': t('ожидается', 'pending', 'күтілуде'), 'paid': t('подтверждена', 'confirmed', 'расталды'),
                'failed': t('не прошла', 'failed', 'өтпеді'), 'cancelled': t('отменена', 'cancelled', 'күші жойылды'),
                'expired': t('срок истёк', 'expired', 'мерзімі аяқталды'), 'refund_requested': t('возврат запрошен', 'refund requested', 'қайтару сұралды'),
                'refunded': t('возвращена', 'refunded', 'қайтарылды'), 'partially_refunded': t('частичный возврат', 'partially refunded', 'ішінара қайтарылды'),
            }
            lines = [f"{order.order_number}: {statuses.get(order.status, order.status)}."]
            payment = getattr(order, 'payment', None)
            if payment:
                lines.append(t('Оплата', 'Payment', 'Төлем') + f": {pay_labels.get(payment.status, payment.status)}; {payment.amount} ₸.")
                if payment.is_test or (payment.provider == 'legacy' and payment.method == 'online'):
                    lines.append(t('Это тестовая платёжная запись; она не подтверждает реальное списание.', 'This is a test payment record, not proof of a real charge.', 'Бұл сынақ төлем жазбасы, нақты ақша алынғанын растамайды.'))
                if payment.method == 'cash' and payment.status == 'pending' and order.status == 'delivered':
                    lines.append(t('JetPoints ожидают подтверждения получения наличных курьером или менеджером: «Заказы → Подробнее → Подтвердить получение наличных». Клиент не может подтвердить свою оплату.', 'JetPoints await cash receipt confirmation by the assigned courier or manager: Orders > Details > Confirm cash received. Customers cannot confirm their own payment.', 'JetPoints үшін курьер не менеджер қолма-қол ақшаның алынғанын растауы керек: «Тапсырыстар → Толығырақ». Клиент өз төлемін растай алмайды.'))
            else:
                lines.append(t('Данные оплаты отсутствуют.', 'Payment information is unavailable.', 'Төлем деректері жоқ.'))
            record = getattr(order, 'loyalty', None)
            if record:
                lines.append(t('Начислено JetPoints', 'JetPoints credited', 'Есептелген JetPoints') + ': ' + display(record.percentage_reward + record.milestone_reward) + ' JP.')
            if order.estimated_arrival_time:
                lines.append(t('Оценка прибытия, не гарантия', 'Estimated arrival, not guaranteed', 'Болжамды келу уақыты, кепілдік емес') + ': ' + timezone.localtime(order.estimated_arrival_time).isoformat())
            sections.append('\n'.join(lines))

    if points:
        account = account_data(User.objects.get(pk=case.customer_id))
        policy = LoyaltyPolicy.current()
        lines = [t('Ваш доступный баланс', 'Your available balance', 'Сіздің қолжетімді балансыңыз') + f": {account['available']} JP = {account['available']} ₸.",
            t('Зарезервировано', 'Reserved', 'Резервте') + f": {account['reserved']} JP."]
        if matches(r'заработ|потрат|всего|total|earned|redeemed|жинал|жұмсал'):
            lines.append(t('Всего начислено / списано (нетто)', 'Total earned / redeemed (net)', 'Барлығы есептелген / жұмсалған (таза)') + f": {display(account['total_earned_minor'])} / {display(account['total_redeemed_minor'])} JP.")
        if matches(r'истор|операц|history|transaction|тарих'):
            entries = account['entries'][:5]
            lines.append(t('Последние операции', 'Recent transactions', 'Соңғы операциялар') + ':')
            lines.extend(f"• {entry['kind']}: {display(entry['amount_minor'])} JP; " + redact_support_text(entry['reason'])[:150] for entry in entries)
            if not entries:
                lines.append(t('Операций пока нет.', 'No transactions yet.', 'Әзірге операциялар жоқ.'))
        if matches(r'правил|услов|процент|уров|как.*(?:работ|начисл|трат)|сколько.*(?:процент|спис)|rate|percent|tier|level|rules|how|пайыз|деңгей|шарт|қалай'):
            level = account['level']
            names = {'bronze': t('Бронзовый', 'Bronze', 'Қола'), 'silver': t('Серебряный', 'Silver', 'Күміс'), 'gold': t('Золотой', 'Gold', 'Алтын')}
            lines.append(t('Ваш уровень', 'Your level', 'Сіздің деңгейіңіз') + ': ' + names.get(level['code'], level['code']) + f"; {level['cashback_percent']}%; " + t('завершённых заказов за месяц', 'completed orders this month', 'осы айдағы аяқталған тапсырыстар') + f": {level['completed_orders']}.")
            lines.append(t(
                f'1 JP = 1 ₸. Bronze: {policy.base_percent}%; Silver: {policy.silver_percent}% после {policy.silver_orders} оплаченных доставленных заказов за текущий месяц; Gold: {policy.gold_percent}% после {policy.gold_orders}. Акционные блюда: {policy.promotional_percent}%, применяется наибольшая подходящая ставка. Списать можно до {policy.spend_percent}% стоимости товаров после скидок в пределах баланса. Доставка исключена. Начисление — на оплаченную деньгами часть после скидок и бонусов, только после оплаты и доставки. Бонусы не сгорают.',
                f'1 JP = 1 KZT. Bronze: {policy.base_percent}%; Silver: {policy.silver_percent}% after {policy.silver_orders} paid/delivered orders this month; Gold: {policy.gold_percent}% after {policy.gold_orders}. Promotional dishes: {policy.promotional_percent}%; the highest applicable rate wins. Redeem up to {policy.spend_percent}% of discounted merchandise, limited by balance. Delivery is excluded. Earn on the money-paid part after discounts and points, only after payment and delivery. Points do not expire.',
                f'1 JP = 1 теңге. Bronze: {policy.base_percent}%; Silver: осы айда төленіп, жеткізілген {policy.silver_orders} тапсырыстан кейін {policy.silver_percent}%; Gold: {policy.gold_orders} тапсырыстан кейін {policy.gold_percent}%. Акциялық тағамдар: {policy.promotional_percent}%, сәйкес ең жоғары мөлшерлеме қолданылады. Жеңілдіктен кейінгі тауар құнының {policy.spend_percent}%-ына дейін, баланс шегінде жұмсауға болады. Жеткізу есепке кірмейді. Ұпай төлем мен жеткізуден кейін, жеңілдіктер мен бонустарды шегергендегі ақшамен төленген бөлікке есептеледі. Мерзімі шектелмеген.'
            ))
        reward = account['second_order']
        if matches(r'втор|second|екінші|1000|1.000'):
            reward_status = {
                'waiting': t('ожидается первый оплаченный доставленный заказ', 'awaiting first paid/delivered order', 'алғашқы төленген жеткізілген тапсырыс күтілуде'),
                'eligible': t('предложение доступно', 'eligible', 'ұсыныс қолжетімді'),
                'awarded': t('начислен', 'awarded', 'есептелді'),
                'expired': t('срок истёк', 'expired', 'мерзімі аяқталды'),
                'reversed': t('отменён после возврата/отмены заказа', 'reversed after refund/cancellation', 'тапсырыс қайтарылғаннан кейін кері алынды'),
                'not_eligible': t('условия не выполнены', 'not eligible', 'шарттар орындалмаған'),
            }
            lines.append(t('Бонус второго заказа', 'Second-order reward', 'Екінші тапсырыс бонусы') + f": {display(reward['reward_minor'])} JP; " + t('период', 'period', 'мерзім') + f': {policy.second_order_days} ' + t('дней', 'days', 'күн') + '. ' + t('Статус', 'Status', 'Күйі') + ': ' + reward_status.get(reward['status'], reward['status']) + '.' + (t(' Срок: ', ' Deadline: ', ' Мерзімі: ') + str(reward['deadline']) if reward['deadline'] else ''))
        lines.append(t('Баланс и история: «Мой профиль → JetPoints». Точный лимит и прогноз для корзины рассчитываются при оформлении.', 'Balance/history: My profile > JetPoints. Exact cart limits and forecast are calculated at checkout.', 'Баланс пен тарих: «Менің профилім → JetPoints». Себеттің нақты шегі мен болжамы рәсімдеу кезінде есептеледі.'))
        sections.append('\n'.join(lines))

    if promo:
        codes = re.findall(r'[A-Za-z0-9_-]{3,50}', ' '.join(questions).upper())[:60]
        found = list(PromoCode.objects.filter(code__in=codes)[:4])
        now = timezone.now()
        for code in found:
            own_uses = PromoRedemption.objects.filter(promo=code, user_id=case.customer_id).count()
            kind = {'percent': code.value.__str__()+'%', 'fixed': str(code.value)+' ₸', 'delivery': t('бесплатная доставка', 'free delivery', 'тегін жеткізу')}[code.kind]
            lines = [f'{code.code}: {kind}.', t('Минимальная сумма товаров', 'Minimum merchandise subtotal', 'Тауарлардың ең төменгі сомасы') + f': {code.minimum_amount} ₸.',
                t('Лимит на аккаунт', 'Per-account limit', 'Аккаунт лимиті') + ': ' + (str(code.per_user_limit) if code.per_user_limit is not None else t('не задан', 'not set', 'белгіленбеген')) + '; ' + t('использовано вами', 'used by you', 'сіз қолданған') + f': {own_uses}.']
            if code.maximum_discount is not None:
                lines.append(t('Максимальная скидка', 'Maximum discount', 'Ең жоғары жеңілдік') + f': {code.maximum_discount} ₸.')
            if code.usage_limit is not None:
                lines.append(t('Осталось общих применений', 'Remaining total uses', 'Қалған жалпы қолдану саны') + f': {max(0, code.usage_limit - code.used_count)}.')
            if code.restaurant_id:
                lines.append(t('Только ресторан', 'Restaurant only', 'Тек мейрамхана') + ': ' + code.restaurant.name)
            if code.starts_at:
                lines.append(t('Начало', 'Starts', 'Басталуы') + ': ' + code.starts_at.isoformat())
            if code.ends_at:
                lines.append(t('Окончание', 'Ends', 'Аяқталуы') + ': ' + code.ends_at.isoformat())
            exhausted = (code.usage_limit is not None and code.used_count >= code.usage_limit) or (code.per_user_limit is not None and own_uses >= code.per_user_limit)
            if not code.is_active or (code.ends_at and code.ends_at < now) or (code.starts_at and code.starts_at > now) or exhausted:
                reasons = []
                if not code.is_active:
                    reasons.append(t('код отключён', 'code is inactive', 'код өшірілген'))
                if code.ends_at and code.ends_at < now:
                    reasons.append(t('срок действия истёк', 'code has expired', 'мерзімі аяқталған'))
                if code.starts_at and code.starts_at > now:
                    reasons.append(t('срок действия ещё не начался', 'code has not started yet', 'қолданылу мерзімі басталмаған'))
                if exhausted:
                    reasons.append(t('лимит использований исчерпан', 'usage limit is exhausted', 'қолдану лимиті таусылған'))
                lines.append(t('Сейчас код недоступен', 'Code is currently unavailable', 'Қазір код қолжетімсіз') + ': ' + '; '.join(reasons) + '.')
            lines.append(t('Окончательную применимость проверит корзина с учётом ресторана, товаров и суммы. Один код на заказ; предпросмотр не расходует лимит, отмена заказа не возвращает использование.', 'The cart verifies final eligibility using restaurant, items and subtotal. One code per order; preview does not consume usage and cancellation does not restore it.', 'Соңғы жарамдылық мейрамхана, тауар мен сома бойынша себетте тексеріледі. Бір тапсырысқа бір код; алдын ала есептеу лимитті жұмсамайды, бас тарту оны қайтармайды.'))
            sections.append('\n'.join(lines))
        if not found:
            sections.append(t('Укажите промокод латиницей, например WELCOME. Без кода, ресторана и суммы товаров нельзя подтвердить скидку.', 'Give the Latin promo code, for example WELCOME. A code, restaurant and merchandise subtotal are needed to verify a discount.', 'Промокодты латын әріптерімен көрсетіңіз, мысалы WELCOME. Жеңілдікті тексеру үшін код, мейрамхана және тауар сомасы қажет.'))

    if matches(r'регист|зарег|register|sign.up|тіркел|без.*телефон|without.*phone'):
        articles.append('verified-registration')
    if matches(r'как.*(?:заказ|оформ)|place.*order|checkout|тапсырыс.*(?:бер|рәсім)'):
        articles.append('verified-checkout')
    if payment_question and not order_question:
        sections.append(t('Онлайн-оплата', 'Online payment', 'Онлайн төлем') + ': ' + (t('настроена', 'configured', 'бапталған') if configured() else t('не настроена; можно выбрать наличные, если этот способ доступен в корзине', 'not configured; choose cash if it is offered at checkout', 'бапталмаған; себетте қолжетімді болса, қолма-қол төлемді таңдаңыз')) + '. ' + (t('Включён тестовый режим провайдера.', 'Provider test mode is enabled.', 'Провайдердің сынақ режимі қосылған.') if settings.FREEDOMPAY_TEST_MODE else ''))
        articles.append('verified-payment')
        if matches(r'истор|мо[ийя].*оплат|history|transactions|төлем.*тарих'):
            from payments.models import Payment
            rows = list(Payment.objects.filter(order__customer_id=case.customer_id).select_related('order').order_by('-created_at', '-id')[:5])
            sections.append(t('Ваши последние оплаты', 'Your recent payments', 'Сіздің соңғы төлемдеріңіз') + ':\n' + ('\n'.join(f'• {row.order.order_number}: {row.status}, {row.amount} ₸' for row in rows) if rows else t('Записей нет.', 'No records.', 'Жазбалар жоқ.')))
    if matches(r'достав|delivery|жеткізу') and not (order_question or explicit_number):
        sections.append(t('Базовая доставка', 'Base delivery fee', 'Негізгі жеткізу құны') + f': {settings.ORDER_DELIVERY_FEE} ₸. ' + t('Итог зависит от условий корзины и промокода. Время доставки — оценка по конкретному заказу, не гарантия.', 'The final fee depends on checkout and promo rules. Delivery time is an order-specific estimate, not a guarantee.', 'Соңғы сома себет пен промокод шарттарына байланысты. Жеткізу уақыты — нақты тапсырыс бойынша болжам, кепілдік емес.'))
    if matches(r'отзыв|review|пікір'):
        articles.append('verified-reviews')
        sections.append(t('Отзыв доступен только владельцу доставленного заказа: один отзыв на заказ, четыре целые оценки от 1 до 5, текст от 10 до 1000 символов. Изменять можно только свой отзыв. В публичный рейтинг входят только одобренные отзывы.', 'Only the owner of a delivered order can review it: one review per order, four integer ratings from 1 to 5, and 10–1000 characters of text. You may edit only your own review. Only approved reviews count toward public ratings.', 'Пікірді тек жеткізілген тапсырыстың иесі қалдыра алады: бір тапсырысқа бір пікір, 1–5 аралығындағы төрт бүтін баға, 10–1000 таңбалы мәтін. Тек өз пікіріңізді өзгерте аласыз. Ашық рейтингке тек мақұлданған пікірлер кіреді.'))
    if matches(r'отмен|возврат|верн[уе]|cancel|refund|қайтар|бас\s+тарт'):
        articles.append('verified-order-actions')
        if matches(r'минут|срок|когда|сколько|when|long|minute|қашан|қанша'):
            sections.append(t('Гарантированный срок возврата в минутах в правилах не задан. Запрос и фактический возврат — разные состояния; результат проверяется в «Платежи».', 'No guaranteed refund deadline in minutes is specified. A request and a completed refund are different states; check Payments for the result.', 'Минутпен кепілдендірілген қайтару мерзімі белгіленбеген. Өтініш пен нақты қайтарым — бөлек күйлер; нәтижені «Төлемдерден» тексеріңіз.'))
    if matches(r'адрес|парол|профил|address|password|profile|мекенжай|құпиясөз'):
        # Do not route a foreign order address query to unrelated profile help.
        if not (order_question or explicit_number):
            articles.append('verified-profile-help')
    if matches(r'что.*(?:умеет|такое).*jetfood|как.*работает.*(?:приложение|jetfood)|what.*jetfood|jetfood.*(?:не істейді|қалай)'):
        articles.append('verified-project-overview')
    for slug in dict.fromkeys(articles):
        entry = FAQ.objects.filter(slug=slug, is_active=True).first()
        if entry:
            sections.append(redact_support_text(getattr(entry, 'answer_'+language))[:1800])
    if len(sections) > 5:
        sections = sections[:5] + [t('Вы спросили о нескольких темах. Уточните следующий вопрос, чтобы разобрать оставшиеся детали.', 'You asked about several topics. Please clarify the next question to cover the remaining details.', 'Бірнеше тақырып сұралды. Қалған мәліметтерді түсіндіру үшін келесі сұрақты нақтылаңыз.')]
    return '\n\n'.join(sections) if sections else None
