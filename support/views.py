from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from .assistant import SupportAIUnavailable, generate_support_reply
from .catalog_answers import catalog_answer
from .service_answers import service_answer
from .models import SupportCase, SupportMessage, FAQ
from .serializers import SupportCaseCreateSerializer, SupportCaseSerializer, SupportMessageInputSerializer

GREETINGS = {'ru': 'Здравствуйте! Опишите проблему. Не отправляйте пароли и платёжные данные.', 'kk': 'Сәлеметсіз бе! Мәселеңізді сипаттаңыз. Құпиясөздер мен төлем деректерін жібермеңіз.', 'en': 'Hello! Describe your problem. Do not send passwords or payment details.'}

class SupportThrottle(UserRateThrottle):
    scope = 'support'


def case_queryset_for(user):
    return SupportCase.objects.filter(customer=user).select_related('order', 'customer').prefetch_related('messages')


def reply_to(case, body=None, request_id=None):
    now = timezone.now()
    claimed = SupportCase.objects.filter(pk=case.pk).filter(Q(ai_busy_until__isnull=True) | Q(ai_busy_until__lt=now)).update(ai_busy_until=now + timedelta(seconds=40))
    if not claimed:
        return Response({'detail': 'A reply is already being generated.'}, status=429)
    try:
        if request_id and case.messages.filter(request_id=request_id).exists():
            return None
        if body:
            SupportMessage.objects.create(support_case=case, sender='customer', body=body, request_id=request_id)
        conversation = list(case.messages.order_by('-id').values('sender', 'body')[:12])[::-1]
        verified = service_answer(case, conversation)
        catalog = catalog_answer(case.language, conversation)
        reply = '\n\n'.join(part for part in (verified, catalog) if part) or None
        source = 'facts' if verified is not None else ('catalog' if catalog is not None else 'ai')
        if reply is None:
            reply = generate_support_reply(case, conversation)
        SupportMessage.objects.create(support_case=case, sender='assistant', source=source, body=reply)
        case.status = 'waiting_for_customer'
        case.save(update_fields=['status', 'updated_at'])
    except SupportAIUnavailable as exc:
        return Response({'detail': exc.detail, 'case_id': case.pk}, status=503)
    finally:
        SupportCase.objects.filter(pk=case.pk).update(ai_busy_until=None)
    return None


class SupportCaseListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [SupportThrottle]

    def get_queryset(self):
        if self.request.user.role != 'customer':
            raise PermissionDenied('Only customers can use the support chat.')
        return case_queryset_for(self.request.user)

    def get_serializer_class(self):
        return SupportCaseCreateSerializer if self.request.method == 'POST' else SupportCaseSerializer

    def create(self, request, *args, **kwargs):
        self.get_queryset()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = serializer.save()
        SupportMessage.objects.create(support_case=case, sender='assistant', body=GREETINGS[case.language])
        if case.issue_description:
            SupportMessage.objects.create(support_case=case, sender='customer', body=case.issue_description)
            if not case.operator_requested:
                failure = reply_to(case)
                if failure is not None:
                    return failure
        return Response(SupportCaseSerializer(case_queryset_for(request.user).get(pk=case.pk)).data, status=201)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([SupportThrottle])
def support_case_message(request, case_id):
    if request.user.role != 'customer':
        raise PermissionDenied('Only customers can use the support chat.')
    case = get_object_or_404(case_queryset_for(request.user), pk=case_id)
    serializer = SupportMessageInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if case.status == 'resolved':
        return Response({'detail': 'This support case is resolved.'}, status=400)
    request_id = serializer.validated_data.get('request_id')
    if request_id and case.messages.filter(request_id=request_id).exists():
        return Response(SupportCaseSerializer(case).data)
    failure = reply_to(case, body=serializer.validated_data['body'], request_id=request_id)
    if failure is not None:
        return failure
    return Response(SupportCaseSerializer(case_queryset_for(request.user).get(pk=case.pk)).data)


@api_view(['GET', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def support_case_detail(request, case_id):
    case = get_object_or_404(case_queryset_for(request.user), pk=case_id)
    if request.method == 'PATCH':
        language = request.data.get('language', case.language)
        if language not in GREETINGS:
            return Response({'language': 'Use ru, kk or en.'}, status=400)
        case.language = language
        if 'order_number' in request.data:
            from orders.models import Order
            number = str(request.data['order_number']).strip()
            order = Order.objects.filter(customer=request.user, order_number__iexact=number).first() if number else None
            if number and order is None:
                return Response({'order_number': 'Enter an order number belonging to your account.'}, status=400)
            case.order = order
            case.order_number = order.order_number if order else ''
        if request.data.get('operator_requested') is True:
            issue = request.data.get('issue_description', '')
            if not isinstance(issue, str) or len(issue) > 4000:
                return Response({'issue_description': 'Use at most 4000 characters.'}, status=400)
            if issue.strip():
                case.issue_description = issue.strip()
                SupportMessage.objects.create(support_case=case, sender='customer', body=issue.strip())
            elif not case.messages.filter(sender='customer').exists():
                return Response({'issue_description': 'Describe the problem before creating an operator request.'}, status=400)
            case.operator_requested = True
            if case.status == 'resolved':
                case.status = 'open'
        case.save(update_fields=['language', 'operator_requested', 'status', 'issue_description', 'order', 'order_number', 'updated_at'])
    return Response(SupportCaseSerializer(case).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([SupportThrottle])
def retry_reply(request, case_id):
    case = get_object_or_404(case_queryset_for(request.user), pk=case_id)
    if case.status == 'resolved' or not case.messages.filter(sender='customer').exists():
        return Response({'detail': 'No pending question.'}, status=400)
    if case.messages.last().sender == 'customer':
        failure = reply_to(case)
        if failure is not None:
            return failure
    return Response(SupportCaseSerializer(case_queryset_for(request.user).get(pk=case.pk)).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def faq(request):
    language = request.query_params.get('language', 'en')
    if language not in GREETINGS:
        language = 'en'
    return Response([{'question': getattr(f, f'question_{language}'), 'answer': getattr(f, f'answer_{language}')} for f in FAQ.objects.filter(is_active=True)])
