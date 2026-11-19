from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .assistant import SupportAIUnavailable, generate_support_reply
from .models import SupportCase, SupportMessage
from .serializers import (
    SupportCaseCreateSerializer,
    SupportCaseSerializer,
    SupportMessageInputSerializer,
)


def case_queryset_for(user):
    return (
        SupportCase.objects.select_related('customer', 'order').prefetch_related(
            Prefetch('messages', queryset=SupportMessage.objects.order_by('created_at', 'id'))
        )
        .filter(customer=user)
    )


class SupportCaseListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'customer':
            raise PermissionDenied('Only customers can use the AI support chat.')
        return case_queryset_for(self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SupportCaseCreateSerializer
        return SupportCaseSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != 'customer':
            raise PermissionDenied('Only customers can use the AI support chat.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = serializer.save()
        SupportMessage.objects.create(
            support_case=case,
            sender='customer',
            body=case.issue_description,
        )
        conversation = list(
            case.messages.order_by('-created_at', '-id').values('sender', 'body')[:12]
        )
        conversation.reverse()
        try:
            reply = generate_support_reply(case, conversation)
        except SupportAIUnavailable as exc:
            return Response(
                {'detail': exc.detail, 'case_id': case.pk},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        SupportMessage.objects.create(
            support_case=case,
            sender='assistant',
            body=reply,
        )
        case.status = 'waiting_for_customer'
        case.save(update_fields=['status', 'updated_at'])
        case = case_queryset_for(request.user).get(pk=case.pk)
        return Response(
            SupportCaseSerializer(case).data,
            status=status.HTTP_201_CREATED,
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def support_case_message(request, case_id):
    if request.user.role != 'customer':
        raise PermissionDenied('Only customers can use the AI support chat.')

    case = get_object_or_404(case_queryset_for(request.user), pk=case_id)
    serializer = SupportMessageInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    body = serializer.validated_data['body']

    if case.status == 'resolved':
        return Response(
            {'detail': 'This support case is resolved. Open a new case if you still need help.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    SupportMessage.objects.create(
        support_case=case,
        sender='customer',
        body=body,
    )
    case.status = 'open'
    case.save(update_fields=['status', 'updated_at'])
    conversation = list(
        case.messages.order_by('-created_at', '-id').values('sender', 'body')[:12]
    )
    conversation.reverse()
    try:
        reply = generate_support_reply(case, conversation)
    except SupportAIUnavailable as exc:
        return Response(
            {'detail': exc.detail, 'case_id': case.pk},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    SupportMessage.objects.create(
        support_case=case,
        sender='assistant',
        body=reply,
    )
    case.status = 'waiting_for_customer'
    case.resolution = ''
    case.save(update_fields=['status', 'resolution', 'updated_at'])

    case = case_queryset_for(request.user).get(pk=case.pk)
    return Response(SupportCaseSerializer(case).data, status=status.HTTP_200_OK)
