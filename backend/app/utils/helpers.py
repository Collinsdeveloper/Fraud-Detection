from flask import request


def paginate(query, serializer):
    """Return a bounded, metadata-rich page from a SQLAlchemy query."""
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    per_page = min(max(request.args.get('per_page', 10, type=int) or 10, 10), 100)
    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        'items': [serializer(item) for item in result.items],
        'pagination': {
            'page': result.page,
            'per_page': result.per_page,
            'total': result.total,
            'pages': result.pages,
            'has_next': result.has_next,
            'has_prev': result.has_prev,
        }
    }


def normalize_msisdn(value, country_code='254'):
    """Normalize a phone number into international format without '+'.

    '0712 345 678' -> '254712345678', '+254712345678' -> '254712345678'
    """
    if not value:
        return value
    digits = ''.join(ch for ch in str(value).strip() if ch.isdigit())
    if not digits:
        return str(value).strip()
    if len(digits) == 9 and str(country_code).startswith('2'):
        return f'{country_code}{digits}'
    if len(digits) == 10 and digits.startswith('0'):
        return f'{country_code}{digits[1:]}'
    if digits.startswith(country_code):
        return digits
    if digits.startswith('+'):
        return digits[1:]
    return digits
