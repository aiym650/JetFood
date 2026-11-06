from django.utils.dateparse import parse_date


def filter_by_created_date(queryset, start_date=None, end_date=None):
    if start_date:
        parsed_start = parse_date(str(start_date))
        if parsed_start:
            queryset = queryset.filter(created_at__date__gte=parsed_start)
        else:
            queryset = queryset.filter(created_at__gte=start_date)

    if end_date:
        parsed_end = parse_date(str(end_date))
        if parsed_end:
            queryset = queryset.filter(created_at__date__lte=parsed_end)
        else:
            queryset = queryset.filter(created_at__lte=end_date)

    return queryset
