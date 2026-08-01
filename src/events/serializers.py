from rest_framework import serializers

from events.models import Event, Place


class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ["id", "name", "city", "address"]


class PlaceWithSeatsPatternSerializer(PlaceSerializer):
    class Meta(PlaceSerializer.Meta):
        fields = [*PlaceSerializer.Meta.fields, "seats_pattern"]


class EventListSerializer(serializers.ModelSerializer):
    place = PlaceSerializer()

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "place",
            "event_time",
            "registration_deadline",
            "status",
            "number_of_visitors",
        ]


class EventDetailSerializer(serializers.ModelSerializer):
    place = PlaceWithSeatsPatternSerializer()

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "place",
            "event_time",
            "registration_deadline",
            "status",
            "number_of_visitors",
        ]
