from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Q
from orders.models import MenuItem, Order
from users.models import User


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search(request):
    """Global search across orders and users"""
    query = request.query_params.get('q', '').strip()
    user = request.user

    if not query:
        return Response({'orders': [], 'users': [], 'menu_items': []})

    # Search orders based on user role
    if user.role == 'admin':
        orders = Order.objects.filter(
            Q(order_number__icontains=query) |
            Q(delivery_address__icontains=query)
        )
    elif user.role == 'manager':
        orders = Order.objects.filter(
            Q(order_number__icontains=query) |
            Q(delivery_address__icontains=query)
        )
    elif user.role == 'delivery':
        orders = Order.objects.filter(
            delivery_person=user
        ).filter(
            Q(order_number__icontains=query) |
            Q(delivery_address__icontains=query)
        )
    else:
        orders = Order.objects.filter(
            customer=user
        ).filter(
            Q(order_number__icontains=query) |
            Q(delivery_address__icontains=query)
        )

    # Search users (admin/manager only)
    if user.role == 'admin':
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
    else:
        users = User.objects.none()

    menu_search_terms = {query}
    menu_term_aliases = {
        'pizza': 'пицца',
        'burger': 'бургер',
        'burgers': 'бургер',
        'soup': 'суп',
        'ramen': 'рамен',
        'sushi': 'суши',
        'roll': 'ролл',
        'salad': 'салат',
        'pasta': 'паста',
        'mexican': 'мексикан',
        'taco': 'тако',
        'tacos': 'тако',
        'meat': 'стейк',
        'steak': 'стейк',
    }
    alias = menu_term_aliases.get(query.strip().casefold())
    if alias:
        menu_search_terms.add(alias)

    menu_search = Q()
    for term in menu_search_terms:
        variants = {term, term.lower(), term.upper(), term.capitalize()}
        for variant in variants:
            menu_search |= (
                Q(name__icontains=variant) |
                Q(description__icontains=variant) |
                Q(category__icontains=variant) |
                Q(name__contains=variant) |
                Q(description__contains=variant) |
                Q(category__contains=variant)
            )
    menu_items = MenuItem.objects.filter(is_active=True).filter(menu_search).values(
        'id', 'name', 'description', 'price', 'category'
    )[:10]

    return Response({
        'orders': list(orders.values('id', 'order_number', 'status', 'total_amount', 'customer__username')[:10]),
        'users': list(users.values('id', 'username', 'email', 'role')[:10]),
        'menu_items': list(menu_items),
    })
