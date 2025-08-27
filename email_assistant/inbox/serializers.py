# serializers.py
from rest_framework import serializers

class EmailSerializer(serializers.Serializer):
    id = serializers.CharField()
    threadId = serializers.CharField(required=False, allow_blank=True)  # Added threadId
    snippet = serializers.CharField(allow_blank=True)
    subject = serializers.CharField(allow_blank=True)
    from_field = serializers.CharField(source="from", allow_blank=True)  # because 'from' is reserved word
    to = serializers.CharField(allow_blank=True, required=False)  # ✅ add this
    date = serializers.CharField(allow_blank=True)
    body_text = serializers.CharField(allow_blank=True)
    
    # Optional: Add validation or custom methods if needed
    def validate_id(self, value):
        """Validate that the ID is not empty"""
        if not value:
            raise serializers.ValidationError("Email ID cannot be empty")
        return value
    
    def to_representation(self, instance):
        """Custom representation if needed"""
        representation = super().to_representation(instance)
        
        # Ensure all fields have proper fallback values
        representation['subject'] = representation.get('subject') or '(no subject)'
        representation['from_field'] = representation.get('from_field') or '(unknown sender)'
        representation['body_text'] = representation.get('body_text') or ''
        
        return representation