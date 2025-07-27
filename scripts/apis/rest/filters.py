import django_filters
from rest.models import AnexoDocumento, AnexoAnexo, AnexoRegistro



class AnexoDocumentoFilters(django_filters.FilterSet):
    pk__in = django_filters.BaseInFilter(field_name="pk", lookup_expr="in")
    creado_en = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = AnexoDocumento
        fields = ["pk__in", "creado_en"]


class AnexoAnexoFilters(django_filters.FilterSet):
    pk__in = django_filters.BaseInFilter(field_name="pk", lookup_expr="in")
    key__in = django_filters.BaseInFilter(field_name="key", lookup_expr="in")
    location = django_filters.CharFilter(field_name="location", lookup_expr="icontains")

    class Meta:
        model = AnexoAnexo
        fields = ["pk__in", "key__in", "location"]


class AnexoRegistroFilters(django_filters.FilterSet):
    documento__in = django_filters.BaseInFilter(field_name="documento", lookup_expr="in")
    anexo__in = django_filters.BaseInFilter(field_name="anexo__key", lookup_expr="in")
    location = django_filters.CharFilter(field_name="anexo__location", lookup_expr="icontains")

    class Meta:
        model = AnexoRegistro
        fields = ["anexo__in", "documento__in", "location"]
